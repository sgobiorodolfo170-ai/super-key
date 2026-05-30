import json
import uuid
import logging
import subprocess
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy import select, func, desc
import os

from app.database import async_session
from app.config import settings
from app.models.provider import Provider
from app.models.channel import Channel
from app.models.ability import Ability
from app.models.model_classification import ModelClassification
from app.models.request_log import RequestLog
from app.models.admin_user import AdminUser
from app.middleware.auth import verify_admin_token, admin_sessions
from app.services.provider_service import ProviderService
from app.services.channel_service import ChannelService
from app.services.preset_service import PresetService
from app.services.api_key_service import ApiKeyService
from app.services.custom_model_service import CustomModelService
from app.utils.crypto import encrypt_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")

HTML_CACHE: str | None = None
STATS_CACHE: dict | None = None
STATS_CACHE_TIME: datetime | None = None
STATS_CACHE_TTL = 30


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/version")
async def get_version():
    try:
        git_hash = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        git_hash = "unknown"
    return {
        "version": git_hash,
        "buildTime": datetime.now().isoformat(),
    }


@router.get("/server-info")
async def server_info(_=Depends(verify_admin_token)):
    return {
        "public_url": settings.public_url,
        "port": settings.port,
    }


@router.get("/stats/overview")
async def stats_overview(_=Depends(verify_admin_token)):
    global STATS_CACHE, STATS_CACHE_TIME
    now = datetime.now()
    if STATS_CACHE is not None and STATS_CACHE_TIME is not None:
        if (now - STATS_CACHE_TIME).total_seconds() < STATS_CACHE_TTL:
            return STATS_CACHE

    async with async_session() as session:
        import asyncio

        async def _count(table):
            return await session.scalar(select(func.count()).select_from(table))

        channel_count, provider_count, model_count, total_requests, avg_latency = await asyncio.gather(
            _count(Channel),
            _count(Provider),
            _count(ModelClassification),
            _count(RequestLog),
            session.scalar(select(func.avg(RequestLog.latency_ms)).where(RequestLog.latency_ms > 0)),
        )

        result = {
            "channels": channel_count or 0,
            "providers": provider_count or 0,
            "models": model_count or 0,
            "total_requests": total_requests or 0,
            "avg_latency_ms": int(avg_latency or 0),
        }
        STATS_CACHE = result
        STATS_CACHE_TIME = now
        return result


@router.get("/providers")
async def list_providers(keyword: str = "", _=Depends(verify_admin_token)):
    providers = await ProviderService.get_all()
    if keyword:
        providers = [p for p in providers if keyword.lower() in p.name.lower() or keyword.lower() in p.code.lower()]
    return {"data": [{"id": p.id, "name": p.name, "code": p.code, "api_base": p.api_base, "website": p.website, "description": p.description, "is_builtin": p.is_builtin, "is_active": p.is_active} for p in providers]}


@router.post("/providers")
async def create_provider(data: dict, _=Depends(verify_admin_token)):
    provider = await ProviderService.create(data)
    return {"data": {"id": provider.id, "name": provider.name, "code": provider.code}}


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: int, data: dict, _=Depends(verify_admin_token)):
    filtered = {k: v for k, v in data.items() if k in PROVIDER_FIELDS}
    provider = await ProviderService.update(provider_id, filtered)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    logger.info("Provider updated: id=%d name=%s fields=%s", provider_id, provider.name, list(filtered.keys()))
    return {"data": {"id": provider.id, "name": provider.name}}


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: int, _=Depends(verify_admin_token)):
    async with async_session() as session:
        provider = await session.get(Provider, provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        name, is_builtin = provider.name, provider.is_builtin
        await session.delete(provider)
        await session.commit()
        logger.info("Provider deleted: id=%d name=%s is_builtin=%s", provider_id, name, is_builtin)
    return {"success": True}


@router.get("/channels")
async def list_channels(_=Depends(verify_admin_token)):
    async with async_session() as session:
        result = await session.execute(select(Channel).order_by(Channel.id.desc()))
        channels = result.scalars().all()
        data = []
        for c in channels:
            model_list = [m.strip() for m in c.models.split(",") if m.strip()] if c.models else []
            data.append({"id": c.id, "name": c.name, "provider_id": c.provider_id, "api_type": c.api_type, "models": c.models, "model_count": len(model_list), "weight": c.weight, "priority": c.priority, "status": c.status, "response_time": c.response_time, "total_requests": c.total_requests, "last_test_time": str(c.last_test_time) if c.last_test_time else None, "enable_auto_complete": c.enable_auto_complete, "remark": c.remark})
        return {"data": data}


CHANNEL_FIELDS = {
    "name", "provider_id", "api_type", "api_key", "api_base", "api_version",
    "models", "model_mapping", "weight", "priority", "status", "auto_ban",
    "enable_auto_complete", "extra_headers", "extra_params", "param_override",
    "timeout", "max_retries", "test_model", "remark"
}

MODEL_FIELDS = {
    "model_id", "model_name", "provider_id", "provider_code", "category",
    "description", "context_window", "max_output_tokens",
    "pricing_input", "pricing_output", "supports_streaming",
    "supports_vision", "supports_function_calling", "supports_tools",
    "is_active", "is_deprecated", "sort_order", "release_date"
}

PROVIDER_FIELDS = {
    "name", "code", "api_base", "website", "description",
    "api_docs_url", "is_active"
}

@router.post("/channels")
async def create_channel(data: dict, _=Depends(verify_admin_token)):
    filtered = {k: v for k, v in data.items() if k in CHANNEL_FIELDS}

    if "provider_id" in filtered:
        filtered["provider_id"] = int(filtered["provider_id"])
    if "weight" in filtered:
        filtered["weight"] = int(filtered.get("weight", 1))
    if "priority" in filtered:
        filtered["priority"] = int(filtered.get("priority", 0))
    if "timeout" in filtered:
        filtered["timeout"] = int(filtered.get("timeout", 60))
    if "max_retries" in filtered:
        filtered["max_retries"] = int(filtered.get("max_retries", 3))
    if "status" in filtered:
        filtered["status"] = int(filtered.get("status", 1))
    if "auto_ban" in filtered:
        filtered["auto_ban"] = int(filtered.get("auto_ban", 1))
    if "enable_auto_complete" in filtered:
        filtered["enable_auto_complete"] = bool(filtered.get("enable_auto_complete", False))

    if "api_key" in data and data["api_key"]:
        filtered["api_key"] = encrypt_api_key(data["api_key"])
    else:
        filtered["api_key"] = encrypt_api_key("")

    if "models" in filtered and isinstance(filtered["models"], list):
        filtered["models"] = ",".join(filtered["models"])

    async with async_session() as session:
        channel = Channel(**filtered)
        session.add(channel)
        await session.commit()
        await session.refresh(channel)

        if filtered.get("models"):
            models = [m.strip() for m in filtered["models"].split(",") if m.strip()]
            await ChannelService.sync_abilities(channel.id, models)

        return {"data": {"id": channel.id, "name": channel.name}}


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: int, data: dict, _=Depends(verify_admin_token)):
    filtered = {k: v for k, v in data.items() if k in CHANNEL_FIELDS}

    if "provider_id" in filtered:
        filtered["provider_id"] = int(filtered["provider_id"])
    if "weight" in filtered:
        filtered["weight"] = int(filtered.get("weight", 1))
    if "priority" in filtered:
        filtered["priority"] = int(filtered.get("priority", 0))
    if "timeout" in filtered:
        filtered["timeout"] = int(filtered.get("timeout", 60))
    if "max_retries" in filtered:
        filtered["max_retries"] = int(filtered.get("max_retries", 3))
    if "status" in filtered:
        filtered["status"] = int(filtered.get("status", 1))
    if "auto_ban" in filtered:
        filtered["auto_ban"] = int(filtered.get("auto_ban", 1))
    if "enable_auto_complete" in filtered:
        filtered["enable_auto_complete"] = bool(filtered.get("enable_auto_complete", False))

    if "api_key" in data and data["api_key"]:
        filtered["api_key"] = encrypt_api_key(data["api_key"])

    if "models" in filtered and isinstance(filtered["models"], list):
        filtered["models"] = ",".join(filtered["models"])

    async with async_session() as session:
        channel = await session.get(Channel, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        for key, value in filtered.items():
            setattr(channel, key, value)
        await session.commit()

        if filtered.get("models"):
            models = [m.strip() for m in filtered["models"].split(",") if m.strip()]
            await ChannelService.sync_abilities(channel_id, models)

        return {"data": {"id": channel.id, "name": channel.name}}


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, _=Depends(verify_admin_token)):
    async with async_session() as session:
        channel = await session.get(Channel, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        await session.delete(channel)
        await session.commit()
    return {"success": True}


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: int, _=Depends(verify_admin_token)):
    result = await ChannelService.test_channel(channel_id)
    return result


@router.post("/channels/{channel_id}/auto-config")
async def auto_config_channel(channel_id: int, _=Depends(verify_admin_token)):
    result = await ChannelService.auto_config(channel_id)
    if "models" in result and result["models"]:
        await ChannelService.sync_abilities(channel_id, result["models"])
    return result


@router.post("/channels/{channel_id}/toggle")
async def toggle_channel(channel_id: int, _=Depends(verify_admin_token)):
    async with async_session() as session:
        channel = await session.get(Channel, channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        channel.status = 0 if channel.status == 1 else 1
        await session.commit()
        return {"data": {"id": channel.id, "status": channel.status}}


@router.post("/channels/auto-detect")
async def auto_detect(data: dict, _=Depends(verify_admin_token)):
    api_base = data.get("api_base", "")
    api_key = data.get("api_key", "")
    if not api_base or not api_key:
        return {"error": "api_base and api_key are required"}
    result = await ChannelService._probe_api(api_base, api_key)
    return result


@router.get("/models")
async def list_models_admin(category: str = "", provider_code: str = "", keyword: str = "", _=Depends(verify_admin_token)):
    async with async_session() as session:
        stmt = select(ModelClassification).order_by(ModelClassification.sort_order)
        if category:
            stmt = stmt.where(ModelClassification.category == category)
        if provider_code:
            stmt = stmt.where(ModelClassification.provider_code == provider_code)
        if keyword:
            kw = f"%{keyword}%"
            stmt = stmt.where(
                ModelClassification.model_id.ilike(kw)
                | ModelClassification.model_name.ilike(kw)
                | ModelClassification.provider_code.ilike(kw)
            )
        result = await session.execute(stmt)
        models = result.scalars().all()

        return {
            "data": [{
                "id": m.id, "model_id": m.model_id, "model_name": m.model_name,
                "provider_code": m.provider_code, "category": m.category,
                "description": m.description, "context_window": m.context_window,
                "max_output_tokens": m.max_output_tokens,
                "pricing_input": m.pricing_input, "pricing_output": m.pricing_output,
                "supports_streaming": m.supports_streaming,
                "supports_vision": m.supports_vision,
                "is_deprecated": m.is_deprecated,
            } for m in models]
        }


@router.get("/models/categories")
async def list_categories_admin(_=Depends(verify_admin_token)):
    from app.routers.relay import MODEL_CATEGORIES, CATEGORY_LABELS
    return {"data": [{"id": cat, "name": CATEGORY_LABELS.get(cat, cat)} for cat in MODEL_CATEGORIES]}


@router.post("/models")
async def create_model(data: dict, _=Depends(verify_admin_token)):
    async with async_session() as session:
        from app.models.model_classification import ModelClassification
        model = ModelClassification(
            model_id=data.get("model_id"),
            model_name=data.get("model_name", ""),
            provider_id=data.get("provider_id"),
            category=data.get("category", "text_generation"),
            context_window=data.get("context_window", 8192),
            pricing_input=data.get("pricing_input", 0),
            pricing_output=data.get("pricing_output", 0),
            supports_streaming=data.get("supports_streaming", True),
            is_active=data.get("is_active", True),
            is_builtin=False
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return {"data": {"id": model.id, "model_id": model.model_id}}


@router.put("/models/{model_id}")
async def update_model(model_id: int, data: dict, _=Depends(verify_admin_token)):
    filtered = {k: v for k, v in data.items() if k in MODEL_FIELDS}
    async with async_session() as session:
        model = await session.get(ModelClassification, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        for key, value in filtered.items():
            setattr(model, key, value)
        await session.commit()
        return {"data": {"id": model.id, "model_id": model.model_id}}


@router.delete("/models/{model_id}")
async def delete_model(model_id: int, _=Depends(verify_admin_token)):
    async with async_session() as session:
        model = await session.get(ModelClassification, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        await session.delete(model)
        await session.commit()
    return {"success": True}


@router.post("/presets/load-providers")
async def load_providers(_=Depends(verify_admin_token)):
    await PresetService.load_providers()
    return {"success": True, "message": "Providers loaded"}


@router.post("/presets/load-models")
async def load_models(_=Depends(verify_admin_token)):
    await PresetService.load_models()
    return {"success": True, "message": "Models loaded"}


@router.get("/presets/status")
async def preset_status(_=Depends(verify_admin_token)):
    async with async_session() as session:
        provider_count = await session.scalar(select(func.count()).select_from(Provider))
        model_count = await session.scalar(select(func.count()).select_from(ModelClassification))
    return {"providers_loaded": provider_count > 0, "models_loaded": model_count > 0, "provider_count": provider_count, "model_count": model_count}


@router.get("/logs")
async def list_logs(model: str = "", is_error: bool = None, page: int = 1, page_size: int = 50, _=Depends(verify_admin_token)):
    async with async_session() as session:
        stmt = select(RequestLog).order_by(RequestLog.id.desc())
        count_stmt = select(func.count()).select_from(RequestLog)
        if model:
            stmt = stmt.where(RequestLog.model == model)
            count_stmt = count_stmt.where(RequestLog.model == model)
        if is_error is not None:
            stmt = stmt.where(RequestLog.is_error == is_error)
            count_stmt = count_stmt.where(RequestLog.is_error == is_error)

        total = await session.scalar(count_stmt)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        logs = result.scalars().all()

        return {
            "data": [{
                "id": l.id, "request_id": l.request_id,
                "channel_id": l.channel_id, "model": l.model,
                "endpoint": l.endpoint, "status_code": l.status_code,
                "latency_ms": l.latency_ms, "input_tokens": l.input_tokens,
                "output_tokens": l.output_tokens, "is_stream": l.is_stream,
                "is_error": l.is_error, "error_message": l.error_message,
                "created_at": str(l.created_at),
            } for l in logs],
            "total": total or 0,
            "page": page,
            "page_size": page_size,
        }


@router.get("/ui", response_class=HTMLResponse)
async def admin_ui():
    global HTML_CACHE
    if HTML_CACHE is not None:
        return HTMLResponse(HTML_CACHE)

    static_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "admin.html")
    if os.path.exists(static_path):
        with open(static_path, "r", encoding="utf-8") as f:
            HTML_CACHE = f.read()
        return HTMLResponse(HTML_CACHE)
    return HTMLResponse("<html><body><h1>Admin Panel</h1><p>admin.html not found. Please create static/admin.html</p></body></html>")


# ==================== API Key 管理 ====================

@router.get("/api-keys")
async def list_api_keys(_=Depends(verify_admin_token)):
    keys = await ApiKeyService.get_all()
    return {"data": [{
        "id": k.id,
        "name": k.name,
        "key": k.key[:10] + "..." + k.key[-4:] if len(k.key) > 14 else k.key,
        "full_key": k.key,
        "models": k.models,
        "is_active": k.is_active,
        "expires_at": str(k.expires_at) if k.expires_at else None,
        "last_used_at": str(k.last_used_at) if k.last_used_at else None,
        "request_count": k.request_count,
        "remark": k.remark,
        "created_at": str(k.created_at),
    } for k in keys]}


@router.post("/api-keys")
async def create_api_key(data: dict, _=Depends(verify_admin_token)):
    api_key = await ApiKeyService.create(data)
    return {"data": {"id": api_key.id, "name": api_key.name, "key": api_key.key}}


@router.get("/api-keys/{api_key_id}")
async def get_api_key(api_key_id: int, _=Depends(verify_admin_token)):
    api_key = await ApiKeyService.get_by_id(api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"data": {
        "id": api_key.id,
        "name": api_key.name,
        "key": api_key.key,
        "models": api_key.models,
        "is_active": api_key.is_active,
        "expires_at": str(api_key.expires_at) if api_key.expires_at else None,
        "last_used_at": str(api_key.last_used_at) if api_key.last_used_at else None,
        "request_count": api_key.request_count,
        "remark": api_key.remark,
        "created_at": str(api_key.created_at),
    }}


@router.put("/api-keys/{api_key_id}")
async def update_api_key(api_key_id: int, data: dict, _=Depends(verify_admin_token)):
    api_key = await ApiKeyService.update(api_key_id, data)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"data": {"id": api_key.id, "name": api_key.name}}


@router.delete("/api-keys/{api_key_id}")
async def delete_api_key(api_key_id: int, _=Depends(verify_admin_token)):
    success = await ApiKeyService.delete(api_key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"success": True}


@router.post("/api-keys/{api_key_id}/regenerate")
async def regenerate_api_key(api_key_id: int, _=Depends(verify_admin_token)):
    api_key = await ApiKeyService.regenerate(api_key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"data": {"id": api_key.id, "key": api_key.key}}


# ==================== 自定义模型管理 ====================

@router.get("/custom-models")
async def list_custom_models(_=Depends(verify_admin_token)):
    models = await CustomModelService.get_all()
    return {"data": [{
        "id": m.id,
        "name": m.name,
        "model_id": m.model_id,
        "description": m.description,
        "selection_mode": m.selection_mode,
        "target_model": m.target_model,
        "channel_id": m.channel_id,
        "channel_model": m.channel_model,
        "is_active": m.is_active,
        "created_at": str(m.created_at),
        "channel_mappings": [{
            "id": cm.id,
            "channel_id": cm.channel_id,
            "target_model": cm.target_model,
            "channel_model": cm.channel_model,
            "weight": cm.weight,
            "is_active": cm.is_active
        } for cm in m.channel_mappings]
    } for m in models]}


@router.post("/custom-models")
async def create_custom_model(data: dict, _=Depends(verify_admin_token)):
    custom_model = await CustomModelService.create(data)
    return {"data": {"id": custom_model.id, "name": custom_model.name, "model_id": custom_model.model_id}}


@router.get("/custom-models/{model_id}")
async def get_custom_model(model_id: int, _=Depends(verify_admin_token)):
    custom_model = await CustomModelService.get_by_id(model_id)
    if not custom_model:
        raise HTTPException(status_code=404, detail="Custom model not found")
    return {"data": {
        "id": custom_model.id,
        "name": custom_model.name,
        "model_id": custom_model.model_id,
        "description": custom_model.description,
        "selection_mode": custom_model.selection_mode,
        "target_model": custom_model.target_model,
        "channel_id": custom_model.channel_id,
        "channel_model": custom_model.channel_model,
        "is_active": custom_model.is_active,
        "created_at": str(custom_model.created_at),
    }}


@router.put("/custom-models/{model_id}")
async def update_custom_model(model_id: int, data: dict, _=Depends(verify_admin_token)):
    custom_model = await CustomModelService.update(model_id, data)
    if not custom_model:
        raise HTTPException(status_code=404, detail="Custom model not found")
    return {"data": {"id": custom_model.id, "name": custom_model.name}}


@router.delete("/custom-models/{model_id}")
async def delete_custom_model(model_id: int, _=Depends(verify_admin_token)):
    success = await CustomModelService.delete(model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Custom model not found")
    return {"success": True}


@router.post("/login")
async def admin_login(username: str = Form(...), password: str = Form(...)):
    async with async_session() as session:
        result = await session.execute(select(AdminUser).where(AdminUser.username == username))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="User is inactive")
        
        if not user.verify_password(password):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=24)
        
        admin_sessions[session_id] = {
            "user_id": user.id,
            "username": user.username,
            "expires_at": expires_at
        }
        
        return {"success": True, "session_id": session_id, "username": user.username}


@router.post("/logout")
async def admin_logout(request: Request):
    session_id = request.headers.get("X-Session-Id", "")
    if session_id in admin_sessions:
        del admin_sessions[session_id]
    return {"success": True}


@router.get("/auth/check")
async def check_auth(request: Request):
    session_id = request.headers.get("X-Session-Id", "")
    if session_id not in admin_sessions:
        return {"authenticated": False}
    
    session = admin_sessions[session_id]
    if session["expires_at"] < datetime.now():
        del admin_sessions[session_id]
        return {"authenticated": False}
    
    session["expires_at"] = datetime.now() + timedelta(hours=24)
    return {"authenticated": True, "username": session["username"]}


@router.post("/change-password")
async def change_password(data: dict, request: Request, _=Depends(verify_admin_token)):
    session_id = request.headers.get("X-Session-Id", "")
    if session_id not in admin_sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = admin_sessions[session_id]
    user_id = session["user_id"]
    
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="Old password and new password are required")
    
    async with async_session() as session_db:
        user = await session_db.get(AdminUser, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.verify_password(old_password):
            raise HTTPException(status_code=400, detail="Old password is incorrect")
        
        user.password_hash = AdminUser.hash_password(new_password)
        await session_db.commit()
    
    return {"success": True, "message": "Password changed successfully"}


@router.post("/change-username")
async def change_username(data: dict, request: Request, _=Depends(verify_admin_token)):
    session_id = request.headers.get("X-Session-Id", "")
    if session_id not in admin_sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = admin_sessions[session_id]
    user_id = session["user_id"]
    
    new_username = data.get("new_username")
    password = data.get("password")
    
    if not new_username:
        raise HTTPException(status_code=400, detail="New username is required")
    
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    
    async with async_session() as session_db:
        user = await session_db.get(AdminUser, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.verify_password(password):
            raise HTTPException(status_code=400, detail="Password is incorrect")
        
        existing_user = await session_db.scalar(select(AdminUser).where(AdminUser.username == new_username))
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        old_username = user.username
        user.username = new_username
        await session_db.commit()
    
    admin_sessions[session_id]["username"] = new_username
    
    return {"success": True, "message": "Username changed successfully", "old_username": old_username, "new_username": new_username}
