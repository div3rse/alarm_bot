from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base, engine
from datetime import datetime
import zoneinfo

zone = zoneinfo.ZoneInfo("Europe/Moscow")

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(tz=zone))  # Учет зоны

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(String, nullable=False)  # Тип уведомления
    message = Column(Text, nullable=False)  # Сообщение
    target_chat_id = Column(Integer, nullable=True)  # Чат для отправки
    notify_date = Column(DateTime, nullable=False)  # Дата уведомления
    is_recurring = Column(Boolean, default=False)  # Повторяемость
    recurrence_rule = Column(Text, nullable=True)  # Правила повторения
    created_at = Column(DateTime, default=lambda: datetime.now(tz=zone))  # Учет зоны
    confirmed = Column(Boolean, default=False)
Base.metadata.create_all(bind=engine)
