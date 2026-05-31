from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from app.database import Base


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), index=True)
    token_hash = Column(String(64), index=True)
    channel_id = Column(Integer, default=0, index=True)
    model = Column(String(255), default="", index=True)
    endpoint = Column(String(255), default="")
    request_size = Column(Integer, default=0)
    response_size = Column(Integer, default=0)
    status_code = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    is_stream = Column(Boolean, default=False)
    is_error = Column(Boolean, default=False, index=True)
    error_type = Column(String(100), default="")
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=func.now(), index=True)
