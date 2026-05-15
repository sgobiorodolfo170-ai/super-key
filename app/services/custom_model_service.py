from sqlalchemy import select
from sqlalchemy.orm import selectinload
import random
from app.database import async_session
from app.models.custom_model import CustomModel
from app.models.custom_model_channel import CustomModelChannel


class CustomModelService:

    @staticmethod
    async def get_all() -> list[CustomModel]:
        async with async_session() as session:
            result = await session.execute(
                select(CustomModel).options(selectinload(CustomModel.channel_mappings)).order_by(CustomModel.id.desc())
            )
            return list(result.unique().scalars().all())

    @staticmethod
    async def get_by_id(model_id: int) -> CustomModel | None:
        async with async_session() as session:
            return await session.get(CustomModel, model_id)

    @staticmethod
    async def get_by_model_id(model_id: str) -> CustomModel | None:
        async with async_session() as session:
            result = await session.execute(
                select(CustomModel).where(CustomModel.model_id == model_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def create(data: dict) -> CustomModel:
        async with async_session() as session:
            channel_mappings = data.pop('channel_mappings', [])
            custom_model = CustomModel(**data)
            session.add(custom_model)
            await session.flush()
            
            for mapping in channel_mappings:
                if mapping.get('channel_id'):
                    channel_mapping = CustomModelChannel(
                        custom_model_id=custom_model.id,
                        channel_id=mapping.get('channel_id'),
                        target_model=mapping.get('target_model', ''),
                        channel_model=mapping.get('channel_model', ''),
                        weight=mapping.get('weight', 1),
                        is_active=True
                    )
                    session.add(channel_mapping)
            
            await session.commit()
            await session.refresh(custom_model)
            return custom_model

    @staticmethod
    async def update(model_id: int, data: dict) -> CustomModel | None:
        async with async_session() as session:
            custom_model = await session.get(CustomModel, model_id)
            if not custom_model:
                return None

            channel_mappings = data.pop('channel_mappings', None)
            
            for key, value in data.items():
                setattr(custom_model, key, value)
            
            if channel_mappings is not None:
                for mapping in custom_model.channel_mappings:
                    await session.delete(mapping)
                
                for mapping in channel_mappings:
                    if mapping.get('channel_id'):
                        channel_mapping = CustomModelChannel(
                            custom_model_id=custom_model.id,
                            channel_id=mapping.get('channel_id'),
                            target_model=mapping.get('target_model', ''),
                            channel_model=mapping.get('channel_model', ''),
                            weight=mapping.get('weight', 1),
                            is_active=True
                        )
                        session.add(channel_mapping)
            
            await session.commit()
            await session.refresh(custom_model)
            return custom_model

    @staticmethod
    async def delete(model_id: int) -> bool:
        async with async_session() as session:
            custom_model = await session.get(CustomModel, model_id)
            if not custom_model:
                return False
            await session.delete(custom_model)
            await session.commit()
            return True

    @staticmethod
    async def resolve_model(model_id: str) -> tuple[str, int | None] | None:
        """
        解析自定义模型，返回 (实际模型名, 渠道ID)
        如果不是自定义模型或模型不存在，返回 None
        """
        async with async_session() as session:
            result = await session.execute(
                select(CustomModel).options(selectinload(CustomModel.channel_mappings)).where(CustomModel.model_id == model_id, CustomModel.is_active == True)
            )
            custom_model = result.scalar_one_or_none()

            if not custom_model:
                return None

            if custom_model.selection_mode == "specific" and custom_model.channel_id:
                # 指定渠道模式：优先使用渠道模型名，否则使用目标模型，最后使用原始模型名
                actual_model = custom_model.channel_model or custom_model.target_model or model_id
                return (actual_model, custom_model.channel_id)
            elif custom_model.selection_mode == "multi" and custom_model.channel_mappings:
                # 多渠道模式：根据权重随机选择一个渠道
                active_mappings = [m for m in custom_model.channel_mappings if m.is_active and m.channel_id]
                if not active_mappings:
                    return (custom_model.target_model or model_id, None)
                
                # 根据权重进行加权随机选择
                total_weight = sum(m.weight for m in active_mappings)
                rand = random.random() * total_weight
                current_weight = 0
                selected_mapping = active_mappings[0]
                
                for mapping in active_mappings:
                    current_weight += mapping.weight
                    if rand <= current_weight:
                        selected_mapping = mapping
                        break
                
                actual_model = selected_mapping.channel_model or selected_mapping.target_model or model_id
                return (actual_model, selected_mapping.channel_id)
            else:
                # 自动选择模式：使用目标模型或原始模型名
                return (custom_model.target_model or model_id, None)
