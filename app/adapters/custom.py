import json
from app.adapters.openai import OpenAIAdaptor


class CustomAdaptor(OpenAIAdaptor):
    api_type = "custom"

    def build_headers(self, channel, original_headers=None):
        headers = super().build_headers(channel, original_headers)
        if channel.extra_headers:
            try:
                extra = json.loads(channel.extra_headers)
                headers.update(extra)
            except (json.JSONDecodeError, TypeError):
                pass
        return headers

    def convert_chat_request(self, channel, openai_request):
        req = super().convert_chat_request(channel, openai_request)
        if channel.extra_params:
            try:
                extra = json.loads(channel.extra_params)
                req.update(extra)
            except (json.JSONDecodeError, TypeError):
                pass
        if channel.param_override:
            try:
                overrides = json.loads(channel.param_override)
                model = req.get("model", "")
                if "default" in overrides:
                    req.update(overrides["default"])
                if model and model in overrides:
                    req.update(overrides[model])
            except (json.JSONDecodeError, TypeError):
                pass
        return req
