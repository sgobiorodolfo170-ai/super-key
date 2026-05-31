import json
import time
import uuid
from app.adapters.base import BaseAdaptor


class ClaudeAdaptor(BaseAdaptor):
    api_type = "claude"

    def build_request_url(self, channel, request_model, endpoint):
        base = (channel.api_base or "https://api.anthropic.com").rstrip("/")
        suffix = "/v1/messages"
        if base.endswith("/v1") and suffix.startswith("/v1/"):
            suffix = suffix[3:]
        return f"{base}{suffix}"

    def build_headers(self, channel, original_headers=None):
        return {
            "x-api-key": channel.api_key,
            "anthropic-version": channel.api_version or "2023-06-01",
            "Content-Type": "application/json",
        }

    def convert_chat_request(self, channel, openai_request):
        messages = openai_request.get("messages", [])
        system_prompts = []
        claude_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                system_prompts.append(content if isinstance(content, str) else str(content))
            elif role == "user":
                claude_messages.append({"role": "user", "content": self._to_claude_content(content)})
            elif role == "assistant":
                claude_messages.append({"role": "assistant", "content": self._to_claude_content(content)})

        claude_request = {
            "model": openai_request.get("model"),
            "messages": claude_messages,
            "max_tokens": openai_request.get("max_tokens", 4096),
            "stream": openai_request.get("stream", False),
        }
        if system_prompts:
            claude_request["system"] = system_prompts if len(system_prompts) > 1 else system_prompts[0]
        if openai_request.get("temperature") is not None:
            claude_request["temperature"] = openai_request["temperature"]
        if openai_request.get("top_p") is not None:
            claude_request["top_p"] = openai_request["top_p"]

        return claude_request

    def _to_claude_content(self, content):
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            claude_content = []
            for item in content:
                if item.get("type") == "text":
                    claude_content.append({"type": "text", "text": item.get("text", "")})
                elif item.get("type") == "image_url":
                    image_url = item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:"):
                        media_type = image_url.split(";")[0].replace("data:", "")
                        data = image_url.split(",", 1)[-1] if "," in image_url else ""
                        claude_content.append({"type": "image", "source": {"type": "base64", "media_type": media_type or "image/jpeg", "data": data}})
            return claude_content
        return str(content)

    def convert_chat_response(self, upstream_response, request_model):
        content_blocks = upstream_response.get("content", [])
        text = "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
        usage = upstream_response.get("usage", {})
        return {
            "id": f"chatcmpl-{upstream_response.get('id', uuid.uuid4().hex[:12])}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request_model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": upstream_response.get("stop_reason", "end_turn")}],
            "usage": {"prompt_tokens": usage.get("input_tokens", 0), "completion_tokens": usage.get("output_tokens", 0), "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)},
        }

    def convert_stream_chunk(self, chunk_line):
        try:
            data = json.loads(chunk_line)
        except (json.JSONDecodeError, TypeError):
            return None

        event_type = data.get("type", "")
        if event_type == "content_block_delta":
            text = data.get("delta", {}).get("text", "")
            return {"id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "object": "chat.completion.chunk", "created": int(time.time()), "choices": [{"index": data.get("index", 0), "delta": {"content": text}}]}
        elif event_type == "message_delta":
            usage = data.get("usage", {})
            return {"id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "object": "chat.completion.chunk", "created": int(time.time()), "choices": [{"index": 0, "delta": {}, "finish_reason": data.get("delta", {}).get("stop_reason")}], "usage": {"prompt_tokens": usage.get("input_tokens", 0), "completion_tokens": usage.get("output_tokens", 0), "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)}}
        return None

    def get_model_list(self, channel):
        if channel.models:
            return [m.strip() for m in channel.models.split(",") if m.strip()]
        return []
