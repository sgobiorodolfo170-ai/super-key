from sqlalchemy import select
from app.database import async_session
from app.models.provider import Provider


class ProviderService:

    @staticmethod
    async def get_all() -> list[Provider]:
        async with async_session() as session:
            result = await session.execute(select(Provider).order_by(Provider.name))
            return list(result.scalars().all())

    @staticmethod
    async def get_by_code(code: str) -> Provider | None:
        async with async_session() as session:
            result = await session.execute(select(Provider).where(Provider.code == code))
            return result.scalar_one_or_none()

    @staticmethod
    async def create(data: dict) -> Provider:
        async with async_session() as session:
            provider = Provider(**data)
            session.add(provider)
            await session.commit()
            await session.refresh(provider)
            return provider

    @staticmethod
    async def update(provider_id: int, data: dict) -> Provider | None:
        async with async_session() as session:
            provider = await session.get(Provider, provider_id)
            if not provider:
                return None
            for key, value in data.items():
                setattr(provider, key, value)
            await session.commit()
            await session.refresh(provider)
            return provider

    @staticmethod
    async def delete(provider_id: int) -> bool:
        async with async_session() as session:
            provider = await session.get(Provider, provider_id)
            if not provider:
                return False
            await session.delete(provider)
            await session.commit()
            return True
