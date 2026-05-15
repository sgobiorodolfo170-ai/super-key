from abc import ABC, abstractmethod


class BaseAdaptor(ABC):
    api_type: str = ""

    @abstractmethod
    def build_request_url(self, channel, request_model: str, endpoint: str) -> str:
        ...

    @abstractmethod
    def build_headers(self, channel, original_headers: dict) -> dict:
        ...

    @abstractmethod
    def convert_chat_request(self, channel, openai_request: dict) -> dict:
        ...

    def convert_image_request(self, channel, openai_request: dict) -> dict:
        raise NotImplementedError

    def convert_embedding_request(self, channel, openai_request: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def convert_chat_response(self, upstream_response: dict, request_model: str) -> dict:
        ...

    @abstractmethod
    def convert_stream_chunk(self, chunk_line: str) -> dict | None:
        ...

    @abstractmethod
    def get_model_list(self, channel) -> list:
        ...
