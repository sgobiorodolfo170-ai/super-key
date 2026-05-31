import random
import logging
import time
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.database import async_session
from app.models.channel import Channel
from app.models.ability import Ability
from app.models.custom_model import CustomModel
from app.models.custom_model_channel import CustomModelChannel

logger = logging.getLogger(__name__)

_custom_model_cache: dict[str, tuple[float, tuple[str, int | None] | None]] = {}
_channel_cache: dict[str, tuple[float, list]] = {}
_cache_ttl = 5.0


class ChannelNotFoundError(Exception):
    pass


class Distributor:

    @staticmethod
    async def resolve_model(model: str) -> tuple[str, int | None]:
        now = time.time()
        cached = _custom_model_cache.get(model)
        if cached and (now - cached[0]) < _cache_ttl:
            result = cached[1]
            if result is not None:
                return result

        async with async_session() as session:
            result = await session.execute(
                select(CustomModel).where(CustomModel.model_id == model, CustomModel.is_active == True)
            )
            custom_model = result.scalar_one_or_none()

            if custom_model:
                if custom_model.selection_mode == "specific" and custom_model.channel_id:
                    actual_model = custom_model.channel_model or custom_model.target_model or model
                    resolved = (actual_model, custom_model.channel_id)
                    _custom_model_cache[model] = (now, resolved)
                    return resolved
                elif custom_model.selection_mode == "multi":
                    result2 = await session.execute(
                        select(CustomModelChannel)
                        .where(CustomModelChannel.custom_model_id == custom_model.id, CustomModelChannel.is_active == True)
                    )
                    mappings = result2.scalars().all()
                    active_mappings = [m for m in mappings if m.channel_id]
                    if active_mappings:
                        total_weight = sum(m.weight for m in active_mappings)
                        rand_val = random.random() * total_weight
                        current_weight = 0
                        selected = active_mappings[0]
                        for mapping in active_mappings:
                            current_weight += mapping.weight
                            if rand_val <= current_weight:
                                selected = mapping
                                break
                        actual_model = selected.channel_model or selected.target_model or model
                        resolved = (actual_model, selected.channel_id)
                        _custom_model_cache[model] = (now, resolved)
                        return resolved
                    resolved = (custom_model.target_model or model, None)
                    _custom_model_cache[model] = (now, resolved)
                    return resolved
                else:
                    resolved = (custom_model.target_model or model, None)
                    _custom_model_cache[model] = (now, resolved)
                    return resolved

            _custom_model_cache[model] = (now, None)
            return (model, None)

    @staticmethod
    async def select_channel(model: str, specific_channel_id: int | None = None) -> Channel:
        if specific_channel_id:
            async with async_session() as session:
                stmt = select(Channel).options(selectinload(Channel.provider)).where(Channel.id == specific_channel_id)
                result = await session.execute(stmt)
                channel = result.scalar_one_or_none()
                if channel and channel.status == 1:
                    return channel
                raise ChannelNotFoundError(f"Channel {specific_channel_id} not available")

        now = time.time()
        cached = _channel_cache.get(model)
        if cached and (now - cached[0]) < _cache_ttl:
            channels = cached[1]
            if channels:
                min_priority = min(c.priority for c in channels)
                candidates = [c for c in channels if c.priority == min_priority]
                total_weight = sum(max(c.weight, 1) for c in candidates)
                rand = random.randint(1, max(total_weight, 1))
                cumulative = 0
                for c in candidates:
                    cumulative += max(c.weight, 1)
                    if rand <= cumulative:
                        return c
                return candidates[-1]
            raise ChannelNotFoundError(f"No channel supports model: {model}")

        async with async_session() as session:
            stmt = (
                select(Channel)
                .options(selectinload(Channel.provider))
                .join(Ability, Channel.id == Ability.channel_id)
                .where(and_(Ability.model == model, Ability.enabled == True, Channel.status == 1))
            )
            result = await session.execute(stmt)
            channels = list(result.unique().scalars().all())

            _channel_cache[model] = (now, channels)

            if not channels:
                raise ChannelNotFoundError(f"No channel supports model: {model}")

            min_priority = min(c.priority for c in channels)
            candidates = [c for c in channels if c.priority == min_priority]

            total_weight = sum(max(c.weight, 1) for c in candidates)
            rand = random.randint(1, max(total_weight, 1))
            cumulative = 0
            for c in candidates:
                cumulative += max(c.weight, 1)
                if rand <= cumulative:
                    logger.debug("Channel selected: id=%d name=%s model=%s priority=%d",
                                 c.id, c.name, model, c.priority)
                    return c
            logger.debug("Channel selected (fallback): id=%d name=%s model=%s",
                         candidates[-1].id, candidates[-1].name, model)
            return candidates[-1]

    @staticmethod
    async def get_candidate_channels(model: str, exclude_ids: list[int] = None) -> list[Channel]:
        """获取所有候选渠道 (排除已失败的)"""
        async with async_session() as session:
            stmt = select(Channel).join(Ability).where(
                and_(Ability.model == model, Ability.enabled == True, Channel.status == 1)
            )
            if exclude_ids:
                stmt = stmt.where(Channel.id.not_in(exclude_ids))
            result = await session.execute(stmt)
            return list(result.scalars().all())
