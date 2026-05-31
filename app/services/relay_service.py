import json
import logging

import httpx
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse
from app.adapters import AdaptorRegistry
from app.services.distributor import Distributor, ChannelNotFoundError
from app.utils.crypto import decrypt_api_key

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=30),
        )
    return _http_client


async def close_http_client():
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


class RelayService:

    CHAT_ENDPOINT = "/v1/chat/completions"

    @staticmethod
    async def relay_chat(request: Request, body: dict):
        model = body.get("model", "")
        if not model:
            return JSONResponse({"error": {"message": "model is required", "type": "invalid_request_error"}}, status_code=400)

        allowed_models = getattr(request.state, "allowed_models", [])
        if allowed_models and model not in allowed_models:
            return JSONResponse({"error": {"message": f"Model '{model}' not allowed for this API key", "type": "permission_error"}}, status_code=403)

        actual_model, specific_channel_id = await Distributor.resolve_model(model)

        try:
            channel = await Distributor.select_channel(actual_model, specific_channel_id)
        except ChannelNotFoundError as e:
            logger.warning("No channel found for model=%s: %s", model, str(e))
            request.state.log_model = model
            request.state.log_channel_id = 0
            request.state.log_is_error = True
            request.state.log_error_message = str(e)
            return JSONResponse({"error": {"message": str(e), "type": "invalid_request_error"}}, status_code=404)

        request.state.log_model = actual_model
        request.state.log_channel_id = channel.id
        request.state.log_is_stream = body.get("stream", False)

        adaptor = AdaptorRegistry.get(channel.api_type)

        api_key = decrypt_api_key(channel.api_key)

        upstream_body = body.copy()
        upstream_body["model"] = actual_model

        upstream_url = adaptor.build_request_url(channel, actual_model, RelayService.CHAT_ENDPOINT)
        upstream_headers = adaptor.build_headers(channel)
        upstream_body = adaptor.convert_chat_request(channel, upstream_body)

        for hdr_key, hdr_val in upstream_headers.items():
            if hdr_key.lower() == "authorization":
                upstream_headers[hdr_key] = f"Bearer {api_key}"
            elif hdr_key.lower() == "x-api-key":
                upstream_headers[hdr_key] = api_key

        is_stream = body.get("stream", False)

        client = _get_http_client()
        timeout = httpx.Timeout(channel.timeout or 60.0, connect=10.0)

        if is_stream:
            return await RelayService._handle_stream(request, client, upstream_url, upstream_headers, upstream_body, adaptor, actual_model, channel, timeout)
        else:
            return await RelayService._handle_non_stream(request, client, upstream_url, upstream_headers, upstream_body, adaptor, actual_model, channel, timeout)

    @staticmethod
    async def _handle_stream(request: Request, client, url, headers, body, adaptor, model, channel, timeout):
        output_tokens = 0
        
        async def generate():
            nonlocal output_tokens
            try:
                async with client.stream("POST", url, headers=headers, json=body, timeout=timeout) as resp:
                    if resp.status_code >= 400:
                        error_text = await resp.aread()
                        request.state.log_is_error = True
                        request.state.log_error_message = error_text.decode()[:500]
                        yield f"data: {json.dumps({'error': {'message': error_text.decode(), 'code': resp.status_code}})}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        if line.startswith(":"):
                            yield line + "\n\n"
                            continue
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk.strip() == "[DONE]":
                                continue
                            converted = adaptor.convert_stream_chunk(chunk)
                            if converted and isinstance(converted, dict):
                                usage = converted.get("usage", {})
                                if usage:
                                    request.state.log_input_tokens = usage.get("prompt_tokens", 0)
                                    output_tokens = usage.get("completion_tokens", 0)
                                    request.state.log_output_tokens = output_tokens
                            if converted:
                                yield f"data: {json.dumps(converted)}\n\n"
                    request.state.log_output_tokens = output_tokens
                    yield "data: [DONE]\n\n"
            except Exception as e:
                request.state.log_is_error = True
                request.state.log_error_message = str(e)[:500]
                logger.exception("Stream error: model=%s channel=%d", model, channel.id if channel else 0)
                yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'stream_error'}})}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

    @staticmethod
    async def _handle_non_stream(request: Request, client, url, headers, body, adaptor, model, channel, timeout):
        try:
            resp = await client.post(url, headers=headers, json=body, timeout=timeout)
            if resp.status_code >= 400:
                logger.warning("Upstream error: url=%s model=%s status=%d body=%s",
                               url, model, resp.status_code, resp.text[:200])
                request.state.log_is_error = True
                request.state.log_error_message = resp.text[:500]
                return JSONResponse({"error": {"message": resp.text, "code": resp.status_code}}, status_code=resp.status_code)
            upstream_data = resp.json()
            converted = adaptor.convert_chat_response(upstream_data, model)
            
            if converted and isinstance(converted, dict):
                usage = converted.get("usage", {})
                if usage:
                    request.state.log_input_tokens = usage.get("prompt_tokens", 0)
                    request.state.log_output_tokens = usage.get("completion_tokens", 0)
            
            return JSONResponse(converted)
        except Exception as e:
            request.state.log_is_error = True
            request.state.log_error_message = str(e)[:500]
            logger.exception("Non-stream error: model=%s channel=%d", model, channel.id if channel else 0)
            return JSONResponse({"error": {"message": str(e), "type": "upstream_error"}}, status_code=502)
