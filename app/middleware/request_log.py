import time

import asyncio
from datetime import datetime
from collections import deque
from starlette.types import ASGIApp, Receive, Scope, Send
from app.database import async_session
from app.models.request_log import RequestLog

_log_queue: deque = deque()
_flush_interval = 2.0
_last_log_flush = time.time()


async def _flush_logs():
    if not _log_queue:
        return
    batch = []
    while _log_queue:
        batch.append(_log_queue.popleft())
    try:
        async with async_session() as session:
            session.add_all(batch)
            await session.commit()
    except Exception:
        pass


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = f"{time.time_ns():x}"
        start_time = time.time()
        status_code_holder = [200]

        async def send_with_capture(message):
            if message["type"] == "http.response.start":
                status_code_holder[0] = message.get("status", 200)
            await send(message)

        await self.app(scope, receive, send_with_capture)

        path = scope.get("path", "")
        if not path.startswith("/admin"):
            latency_ms = int((time.time() - start_time) * 1000)
            headers_list = scope.get("headers", [])
            auth_header = ""
            for k, v in headers_list:
                if k == b"authorization":
                    auth_header = v.decode()
                    break
            token_hash = auth_header.split(" ")[-1][:64] if auth_header else ""

            state = scope.get("state")
            model = getattr(state, "log_model", "") if state else ""
            channel_id = getattr(state, "log_channel_id", 0) if state else 0
            input_tokens = getattr(state, "log_input_tokens", 0) if state else 0
            output_tokens = getattr(state, "log_output_tokens", 0) if state else 0
            is_stream = getattr(state, "log_is_stream", False) if state else False
            log_error_message = getattr(state, "log_error_message", "") if state else ""
            log_is_error = getattr(state, "log_is_error", False) if state else False

            error_message = log_error_message or (f"HTTP {status_code_holder[0]}" if status_code_holder[0] >= 400 else "")
            is_error = log_is_error or status_code_holder[0] >= 400

            log_entry = RequestLog(
                request_id=request_id,
                token_hash=token_hash,
                channel_id=channel_id,
                model=model,
                endpoint=path,
                status_code=status_code_holder[0],
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                is_stream=is_stream,
                is_error=is_error,
                error_message=error_message,
                created_at=datetime.now()
            )
            _log_queue.append(log_entry)

            now = time.time()
            global _last_log_flush
            if now - _last_log_flush > _flush_interval:
                _last_log_flush = now
                asyncio.create_task(_flush_logs())