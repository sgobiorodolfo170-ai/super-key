from datetime import datetime, timedelta
import logging
from fastapi import Request, HTTPException
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.api_key import ApiKey

logger = logging.getLogger(__name__)

admin_sessions = {}


async def verify_api_token(request: Request):
    """
    验证 API Token，支持：
    1. 配置中的单一 Token（向后兼容）
    2. 数据库中的 API Key
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing API token")

    if token == settings.api_token:
        request.state.api_key = None
        request.state.allowed_models = []
        return

    async with async_session() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.key == token))
        key_obj = result.scalar_one_or_none()

        if not key_obj:
            logger.warning("API auth failed: invalid token prefix=%s...", token[:10] if len(token) > 10 else token)
            raise HTTPException(status_code=401, detail="Invalid API token")

        if not key_obj.is_active:
            logger.warning("API auth failed: key '%s' is disabled", key_obj.name)
            raise HTTPException(status_code=401, detail="API key is disabled")

        if key_obj.expires_at and key_obj.expires_at < datetime.now():
            logger.warning("API auth failed: key '%s' has expired", key_obj.name)
            raise HTTPException(status_code=401, detail="API key has expired")

        allowed_models = [m.strip() for m in (key_obj.models or "").split(",") if m.strip()]

        request.state.api_key = key_obj
        request.state.allowed_models = allowed_models

        key_obj.last_used_at = datetime.now()
        key_obj.request_count = (key_obj.request_count or 0) + 1
        await session.commit()


async def verify_admin_token(request: Request):
    """
    验证管理员权限，支持：
    1. 传统的 X-Admin-Token
    2. 会话认证 X-Session-Id
    """
    session_id = request.headers.get("X-Session-Id", "")
    if session_id and session_id in admin_sessions:
        session = admin_sessions[session_id]
        if session["expires_at"] < datetime.now():
            del admin_sessions[session_id]
            logger.info("Admin session expired: session_id=%s...", session_id[:8])
            raise HTTPException(status_code=401, detail="Session expired")
        session["expires_at"] = datetime.now() + timedelta(hours=24)
        request.state.admin_user = session["username"]
        return

    token = request.headers.get("X-Admin-Token", "")
    if token == settings.admin_token:
        return

    raise HTTPException(status_code=401, detail="Invalid admin token")
