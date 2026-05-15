import time
import uuid
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import async_session
from app.models.request_log import RequestLog


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()
        response = None
        error_message = ""
        is_error = False
        status_code = 200

        try:
            response = await call_next(request)
            status_code = response.status_code
            
            if status_code >= 400:
                is_error = True
                error_message = f"HTTP {status_code}"
                
        except Exception as e:
            is_error = True
            error_message = str(e)
            raise
        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            
            if request.url.path.startswith("/admin"):
                pass
            else:
                async with async_session() as session:
                    try:
                        token_hash = request.headers.get("authorization", "").split(" ")[-1][:64] if request.headers.get("authorization") else ""
                        
                        model = getattr(request.state, "log_model", "")
                        channel_id = getattr(request.state, "log_channel_id", 0)
                        input_tokens = getattr(request.state, "log_input_tokens", 0)
                        output_tokens = getattr(request.state, "log_output_tokens", 0)
                        is_stream = getattr(request.state, "log_is_stream", False)
                        log_error_message = getattr(request.state, "log_error_message", "")
                        log_is_error = getattr(request.state, "log_is_error", is_error)
                        
                        if log_error_message:
                            error_message = log_error_message
                        is_error = log_is_error
                        
                        log_entry = RequestLog(
                            request_id=request_id,
                            token_hash=token_hash,
                            channel_id=channel_id,
                            model=model,
                            endpoint=request.url.path,
                            status_code=status_code,
                            latency_ms=latency_ms,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            is_stream=is_stream,
                            is_error=is_error,
                            error_message=error_message,
                            created_at=datetime.now()
                        )
                        session.add(log_entry)
                        await session.commit()
                    except Exception as e:
                        pass

        return response if response else Response(status_code=500)