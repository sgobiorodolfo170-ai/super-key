from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, func
from app.database import Base


class ModelClassification(Base):
    __tablename__ = "model_classifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(255), unique=True, nullable=False)
    model_name = Column(String(255), nullable=False)
    provider_code = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    description = Column(Text, default="")
    context_window = Column(Integer, default=0)
    max_output_tokens = Column(Integer, default=0)
    pricing_input = Column(Float, default=0.0)
    pricing_output = Column(Float, default=0.0)
    is_free = Column(Boolean, default=False)
    supports_streaming = Column(Boolean, default=True)
    supports_vision = Column(Boolean, default=False)
    supports_function_calling = Column(Boolean, default=False)
    supports_tools = Column(Boolean, default=False)
    release_date = Column(String(20), default="")
    is_deprecated = Column(Boolean, default=False)
    is_builtin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
