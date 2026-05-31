from datetime import datetime, timedelta
import asyncio
import logging
import time
from collections import deque
from fastapi import Request, HTTPException
from sqlalchemy import select, update, func, delete

from app.config import settings
from app.database import async_session
from app.models.api_key import ApiKey
from app.models.admin_session import AdminSession

logger = logging.getLogger(__name__)

_api_key_cache: dict[str, tuple[float, ApiKey | None, list[str]]] = {}
_api_key_cache_ttl = 10.0
_usage_batch: deque[tuple[int, datetime]] = deque()
_usage_flush_interval = 30.0
_last_flush = time.time()


async def _flush_usage_batch():
    if not _usage_batch:
        return
    counts: dict[int, tuple[int, datetime]] = {}
    now = datetime.now()
    while _usage_batch:
        key_id, ts = _usage_batch.popleft()
        if key_id in counts:
            c, _ = counts[key_id]
            counts[key_id] = (c + 1, ts or now)
        else:
            counts[key_id] = (1, ts or now)
    try:
        async with async_session() as session:
            for key_id, (cnt, ts) in counts.items():
                await session.execute(
                    update(ApiKey)
                    .where(ApiKey.id == key_id)
                    .values(last_used_at=ts, request_count=func.coalesce(ApiKey.request_count, 0) + cnt)
                )
            await session.commit()
    except Exception:
        logger.warning("Failed to flush usage batch", exc_info=True)


async def verify_api_token(request: Request):
    global _last_flush
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing API token")

    if token == settings.api_token:
        request.state.api_key = None
        request.state.allowed_models = []
        return

    now = time.time()
    cached = _api_key_cache.get(token)
    if cached and (now - cached[0]) < _api_key_cache_ttl:
        key_obj, allowed_models = cached[1], cached[2]
        if not key_obj:
            raise HTTPException(status_code=401, detail="Invalid API token")
        if not key_obj.is_active:
            raise HTTPException(status_code=401, detail="API key is disabled")
        if key_obj.expires_at and key_obj.expires_at < datetime.now():
            raise HTTPException(status_code=401, detail="API key has expired")
        request.state.api_key = key_obj
        request.state.allowed_models = allowed_models
        _usage_batch.append((key_obj.id, None))
        if now - _last_flush > _usage_flush_interval:
            _last_flush = now
            asyncio.create_task(_flush_usage_batch())
        return

    async with async_session() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.key == token))
        key_obj = result.scalar_one_or_none()

        if not key_obj:
            _api_key_cache[token] = (now, None, [])
            logger.warning("API auth failed: invalid token prefix=%s...", token[:10] if len(token) > 10 else token)
            raise HTTPException(status_code=401, detail="Invalid API token")

        if not key_obj.is_active:
            raise HTTPException(status_code=401, detail="API key is disabled")

        if key_obj.expires_at and key_obj.expires_at < datetime.now():
            raise HTTPException(status_code=401, detail="API key has expired")

        allowed_models = [m.strip() for m in (key_obj.models or "").split(",") if m.strip()]

        _api_key_cache[token] = (now, key_obj, allowed_models)
        request.state.api_key = key_obj
        request.state.allowed_models = allowed_models

        _usage_batch.append((key_obj.id, None))
        if now - _last_flush > _usage_flush_interval:
            _last_flush = now
            asyncio.create_task(_flush_usage_batch())


async def verify_admin_token(request: Request):
    session_id = request.headers.get("X-Session-Id", "")
    if session_id:
        async with async_session() as session:
            result = await session.execute(
                select(AdminSession).where(AdminSession.session_id == session_id)
            )
            sess = result.scalar_one_or_none()
            if not sess:
                raise HTTPException(status_code=401, detail="Session expired")
            if sess.expires_at < datetime.now():
                await session.execute(delete(AdminSession).where(AdminSession.session_id == session_id))
                await session.commit()
                logger.info("Admin session expired: session_id=%s...", session_id[:8])
                raise HTTPException(status_code=401, detail="Session expired")
            sess.expires_at = datetime.now() + timedelta(hours=24)
            await session.commit()
            request.state.admin_user = sess.username
            request.state.admin_user_id = sess.user_id
            return

    token = request.headers.get("X-Admin-Token", "")
    if token == settings.admin_token:
        request.state.admin_user = "admin"
        request.state.admin_user_id = None
        return

    raise HTTPException(status_code=401, detail="Invalid admin token")
