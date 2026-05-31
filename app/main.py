import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.config import settings
from app.services.preset_service import PresetService
from app.services.relay_service import close_http_client
from app.utils.logger import setup_logger
from app.routers import relay, admin

from app.middleware.request_log import RequestLogMiddleware

setup_logger(level=settings.log_level)
logger = logging.getLogger("super-key")

SESSION_CLEANUP_INTERVAL = 300


async def _cleanup_expired_sessions():
    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)
        from datetime import datetime
        from app.models.admin_session import AdminSession
        from sqlalchemy import delete
        try:
            async with async_session() as session:
                result = await session.execute(
                    delete(AdminSession).where(AdminSession.expires_at < datetime.now())
                )
                await session.commit()
                if result.rowcount:
                    logger.debug("Cleaned up %d expired admin sessions", result.rowcount)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Super-Key starting up...")
    
    # 安全检查：拒绝默认弱密钥
    insecure_configs = []
    if settings.api_token == "sk-super-key-change-me":
        insecure_configs.append("SUPER_KEY_API_TOKEN")
    if settings.admin_token == "admin-change-me":
        insecure_configs.append("SUPER_KEY_ADMIN_TOKEN or ADMIN_TOKEN")
    if settings.encryption_key == "super-key-32-byte-encryption-key!":
        insecure_configs.append("SUPER_KEY_ENCRYPTION_KEY")
    
    if insecure_configs:
        logger.warning("⚠️  SECURITY WARNING: Using default insecure values for: %s", ", ".join(insecure_configs))
        logger.warning("⚠️  Please set strong random values in environment variables before production deployment!")
    
    await init_db()
    await PresetService.load_all_if_empty()

    cleanup_task = asyncio.create_task(_cleanup_expired_sessions())

    logger.info("Super-Key startup complete")
    yield


    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    from app.middleware.request_log import _flush_logs
    from app.middleware.auth import _flush_usage_batch
    await _flush_logs()
    await _flush_usage_batch()
    await close_http_client()
    logger.info("Super-Key shut down")


app = FastAPI(title="Super-Key", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLogMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from fastapi.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": exc.detail, "type": "http_error"}},
        )
    
    exc_str = str(exc)
    exc_type = type(exc).__name__
    
    if "no such column" in exc_str or "OperationalError" in exc_type:
        logger.error("Database schema error on %s %s: %s", request.method, request.url.path, exc_str)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Database schema mismatch. Please restart the server to auto-migrate.",
                    "type": "db_schema_error",
                    "detail": exc_str[:200]
                }
            },
        )
    
    if "database is locked" in exc_str:
        logger.error("Database locked on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=503,
            content={"error": {"message": "Database is temporarily locked. Please retry.", "type": "db_locked"}},
        )
    
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc_str, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"message": "Internal server error", "type": "internal_error"}},
    )

app.include_router(relay.router)
app.include_router(admin.router)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass
