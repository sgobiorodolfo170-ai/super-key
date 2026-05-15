from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class CustomModel(Base):
    __tablename__ = "custom_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    model_id = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")

    selection_mode = Column(String(20), default="auto")
    target_model = Column(String(100), default="")
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    channel_model = Column(String(100), default="")

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    channel = relationship("Channel", back_populates="custom_models")
    channel_mappings = relationship("CustomModelChannel", back_populates="custom_model", cascade="all, delete-orphan")
