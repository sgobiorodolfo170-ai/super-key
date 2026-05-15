from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    api_type = Column(String(30), nullable=False)
    api_key = Column(Text, nullable=False)
    api_base = Column(String(500), default="")
    api_version = Column(String(50), default="")
    models = Column(Text, default="")
    model_mapping = Column(Text, default="")
    weight = Column(Integer, default=1)
    priority = Column(Integer, default=0)
    status = Column(Integer, default=1)
    auto_ban = Column(Integer, default=1)
    enable_auto_complete = Column(Boolean, default=False)
    extra_headers = Column(Text, default="")
    extra_params = Column(Text, default="")
    param_override = Column(Text, default="")
    timeout = Column(Integer, default=60)
    max_retries = Column(Integer, default=3)
    response_time = Column(Integer, default=0)
    total_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    last_test_time = Column(DateTime, nullable=True)
    test_model = Column(String(100), default="")
    remark = Column(String(500), default="")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    provider = relationship("Provider", back_populates="channels")
    abilities = relationship("Ability", back_populates="channel", cascade="all, delete-orphan")
    custom_models = relationship("CustomModel", back_populates="channel")
