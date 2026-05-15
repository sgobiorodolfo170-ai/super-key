from app.adapters.registry import AdaptorRegistry
from app.adapters.openai import OpenAIAdaptor
from app.adapters.gemini import GeminiAdaptor
from app.adapters.claude import ClaudeAdaptor
from app.adapters.custom import CustomAdaptor

AdaptorRegistry.register(OpenAIAdaptor)
AdaptorRegistry.register(GeminiAdaptor)
AdaptorRegistry.register(ClaudeAdaptor)
AdaptorRegistry.register(CustomAdaptor)

__all__ = ["AdaptorRegistry", "OpenAIAdaptor", "GeminiAdaptor", "ClaudeAdaptor", "CustomAdaptor"]
