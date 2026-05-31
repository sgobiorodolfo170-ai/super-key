from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    user_id = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)