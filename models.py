# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, unique=True, index=True)
    username = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String)

    notifications = relationship("Notification", back_populates="user")

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    target_chat_id = Column(Integer, nullable=True)
    notify_date = Column(DateTime, nullable=False)
    next_notify_date = Column(DateTime, nullable=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(MOSCOW_TZ))
    confirmed = Column(Boolean, default=False)
    last_message_id = Column(Integer, nullable=True)

    user = relationship("User", back_populates="notifications")