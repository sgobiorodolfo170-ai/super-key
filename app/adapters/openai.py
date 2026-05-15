import json
from app.adapters.base import BaseAdaptor


class OpenAIAdaptor(BaseAdaptor):
    api_type = "openai"

    def build_request_url(self, channel, request_model, endpoint):
        base = (channel.api_base or (channel.provider.api_base if channel.provider else "")).rstrip("/")
        return f"{base}{endpoint}"

    def build_headers(self, channel, original_headers=None):
        return {
            "Authorization": f"Bearer {channel.api_key}",
            "Content-Type": "application/json",
        }

    def convert_chat_request(self, channel, openai_request):
        req = openai_request.copy()
        if channel.model_mapping:
            try:
                mapping = json.loads(channel.model_mapping)
                model = req.get("model", "")
                if model in mapping:
                    req["model"] = mapping[model]
            except (json.JSONDecodeError, TypeError):
                pass
        return req

    def convert_chat_response(self, upstream_response, request_model):
        return upstream_response

    def convert_stream_chunk(self, chunk_line):
        try:
            return json.loads(chunk_line)
        except (json.JSONDecodeError, TypeError):
            return None

    def get_model_list(self, channel):
        if channel.models:
            return [m.strip() for m in channel.models.split(",") if m.strip()]
        return []
