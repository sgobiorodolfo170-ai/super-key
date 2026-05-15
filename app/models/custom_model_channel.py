from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class CustomModelChannel(Base):
    __tablename__ = "custom_model_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    custom_model_id = Column(Integer, ForeignKey("custom_models.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    target_model = Column(String(100), default="")
    channel_model = Column(String(100), default="")
    weight = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    custom_model = relationship("CustomModel", back_populates="channel_mappings")
    channel = relationship("Channel")
