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
from app.utils.logger import setup_logger
from app.routers import relay, admin
from app.middleware.auth import admin_sessions

setup_logger(level=settings.log_level)
logger = logging.getLogger("super-key")

SESSION_CLEANUP_INTERVAL = 300


async def _cleanup_expired_sessions():
    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)
        from datetime import datetime
        expired = [
            sid for sid, s in list(admin_sessions.items())
            if s["expires_at"] < datetime.now()
        ]
        for sid in expired:
            del admin_sessions[sid]
        if expired:
            logger.debug("Cleaned up %d expired admin sessions", len(expired))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Super-Key starting up...")
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
    logger.info("Super-Key shut down")


app = FastAPI(title="Super-Key", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from fastapi.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": exc.detail, "type": "http_error"}},
        )
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
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
