from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Ability(Base):
    __tablename__ = "abilities"
    __table_args__ = (UniqueConstraint("channel_id", "model", name="uq_channel_model"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)
    model = Column(String(255), nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    weight = Column(Integer, default=1)
    priority = Column(Integer, default=0)
    tag = Column(String(100), default="")

    channel = relationship("Channel", back_populates="abilities")
