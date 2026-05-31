import secrets
from datetime import datetime
from sqlalchemy import select
from app.database import async_session
from app.models.api_key import ApiKey


class ApiKeyService:

    @staticmethod
    def generate_key() -> str:
        return f"sk-{secrets.token_hex(24)}"

    @staticmethod
    async def get_all() -> list[ApiKey]:
        async with async_session() as session:
            result = await session.execute(select(ApiKey).order_by(ApiKey.id.desc()))
            return list(result.scalars().all())

    @staticmethod
    async def get_by_id(api_key_id: int) -> ApiKey | None:
        async with async_session() as session:
            return await session.get(ApiKey, api_key_id)

    @staticmethod
    async def get_by_key(key: str) -> ApiKey | None:
        async with async_session() as session:
            result = await session.execute(select(ApiKey).where(ApiKey.key == key))
            return result.scalar_one_or_none()

    @staticmethod
    async def create(data: dict) -> ApiKey:
        async with async_session() as session:
            if "key" not in data or not data["key"]:
                data["key"] = ApiKeyService.generate_key()

            if "models" in data and isinstance(data["models"], list):
                data["models"] = ",".join(data["models"])

            api_key = ApiKey(**data)
            session.add(api_key)
            await session.commit()
            await session.refresh(api_key)
            return api_key

    @staticmethod
    async def update(api_key_id: int, data: dict) -> ApiKey | None:
        async with async_session() as session:
            api_key = await session.get(ApiKey, api_key_id)
            if not api_key:
                return None

            if "models" in data and isinstance(data["models"], list):
                data["models"] = ",".join(data["models"])

            if "expires_at" in data and isinstance(data["expires_at"], str):
                try:
                    data["expires_at"] = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    data["expires_at"] = None

            for key, value in data.items():
                if key != "key":
                    setattr(api_key, key, value)
            await session.commit()
            await session.refresh(api_key)
            return api_key

    @staticmethod
    async def delete(api_key_id: int) -> bool:
        async with async_session() as session:
            api_key = await session.get(ApiKey, api_key_id)
            if not api_key:
                return False
            await session.delete(api_key)
            await session.commit()
            return True

    @staticmethod
    async def regenerate(api_key_id: int) -> ApiKey | None:
        async with async_session() as session:
            api_key = await session.get(ApiKey, api_key_id)
            if not api_key:
                return None
            api_key.key = ApiKeyService.generate_key()
            await session.commit()
            await session.refresh(api_key)
            return api_key

    @staticmethod
    async def validate_key(key: str) -> tuple[ApiKey | None, str | None]:
        """
        验证 API Key，返回 (ApiKey对象, 错误信息)
        """
        async with async_session() as session:
            result = await session.execute(select(ApiKey).where(ApiKey.key == key))
            api_key = result.scalar_one_or_none()

            if not api_key:
                return None, "Invalid API key"

            if not api_key.is_active:
                return None, "API key is disabled"

            if api_key.expires_at and api_key.expires_at < datetime.now():
                return None, "API key has expired"

            return api_key, None
