from app.adapters.base import BaseAdaptor


class AdaptorRegistry:
    _adaptors: dict[str, type[BaseAdaptor]] = {}

    @classmethod
    def register(cls, adaptor_class: type[BaseAdaptor]):
        cls._adaptors[adaptor_class.api_type] = adaptor_class

    @classmethod
    def get(cls, api_type: str) -> BaseAdaptor:
        adaptor_class = cls._adaptors.get(api_type)
        if adaptor_class is None:
            raise ValueError(f"Unknown api_type: {api_type}")
        return adaptor_class()
