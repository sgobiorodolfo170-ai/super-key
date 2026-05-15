import json
import time
import uuid
from app.adapters.base import BaseAdaptor


class GeminiAdaptor(BaseAdaptor):
    api_type = "gemini"

    def build_request_url(self, channel, request_model, endpoint):
        base = (channel.api_base or "https://generativelanguage.googleapis.com").rstrip("/")
        version = channel.api_version or "v1beta"
        suffix = ":streamGenerateContent?alt=sse" if endpoint == "/v1/chat/completions" else ":generateContent"
        return f"{base}/{version}/models/{request_model}{suffix}"

    def build_headers(self, channel, original_headers=None):
        return {"Content-Type": "application/json"}

    def convert_chat_request(self, channel, openai_request):
        messages = openai_request.get("messages", [])
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")
            if role == "system":
                system_instruction = {"parts": [{"text": content if isinstance(content, str) else str(content)}]}
                continue
            gemini_role = "model" if role == "assistant" else "user"
            parts = self._content_to_parts(content)
            contents.append({"role": gemini_role, "parts": parts})

        gemini_request = {"contents": contents, "generationConfig": {}}
        if system_instruction:
            gemini_request["systemInstruction"] = system_instruction
        if openai_request.get("max_tokens"):
            gemini_request["generationConfig"]["maxOutputTokens"] = openai_request["max_tokens"]
        if openai_request.get("temperature") is not None:
            gemini_request["generationConfig"]["temperature"] = openai_request["temperature"]
        if openai_request.get("top_p") is not None:
            gemini_request["generationConfig"]["topP"] = openai_request["top_p"]

        return gemini_request

    def _content_to_parts(self, content):
        if isinstance(content, str):
            return [{"text": content}]
        if isinstance(content, list):
            parts = []
            for item in content:
                if item.get("type") == "text":
                    parts.append({"text": item.get("text", "")})
                elif item.get("type") == "image_url":
                    image_url = item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:"):
                        mime_type = image_url.split(";")[0].replace("data:", "")
                        data = image_url.split(",", 1)[-1] if "," in image_url else ""
                        parts.append({"inlineData": {"mimeType": mime_type or "image/jpeg", "data": data}})
            return parts if parts else [{"text": ""}]
        return [{"text": str(content)}]

    def convert_chat_response(self, upstream_response, request_model):
        candidates = upstream_response.get("candidates", [])
        usage = upstream_response.get("usageMetadata", {})
        choices = []
        for i, candidate in enumerate(candidates):
            content_obj = candidate.get("content", {})
            parts = content_obj.get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            choices.append({"index": i, "message": {"role": "assistant", "content": text}, "finish_reason": candidate.get("finishReason", "STOP")})

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request_model,
            "choices": choices,
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
        }

    def convert_stream_chunk(self, chunk_line):
        try:
            data = json.loads(chunk_line)
        except (json.JSONDecodeError, TypeError):
            return None

        candidates = data.get("candidates", [])
        if not candidates:
            return None

        choices = []
        for c in candidates:
            parts = c.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            choices.append({"index": c.get("index", 0), "delta": {"content": text} if text else {}, "finish_reason": c.get("finishReason")})

        return {"id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "object": "chat.completion.chunk", "created": int(time.time()), "choices": choices}

    def get_model_list(self, channel):
        if channel.models:
            return [m.strip() for m in channel.models.split(",") if m.strip()]
        return []
