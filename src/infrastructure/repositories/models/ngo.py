"""
Модель данных для НКО (Non-Governmental Organization)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from . import Base


class NGO(Base):
    """
    Модель для хранения информации об НКО пользователей
    """
    __tablename__ = "ngos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False, comment="ID пользователя Telegram")
    
    # Основная информация об НКО
    ngo_name = Column(String(255), nullable=False, comment="Название НКО")
    description = Column(Text, nullable=True, comment="Описание деятельности НКО")
    activities = Column(Text, nullable=True, comment="Формы деятельности НКО")
    contact = Column(Text, nullable=True, comment="Контактная информация")
    
    # Метаданные
    is_active = Column(Boolean, default=True, comment="Активна ли запись")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Дата создания")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Дата обновления")
    
    def __repr__(self) -> str:
        return f"<NGO(id={self.id}, user_id={self.user_id}, name='{self.ngo_name}')>"
    
    def to_dict(self) -> dict:
        """Преобразование модели в словарь для удобства использования"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ngo_name": self.ngo_name,
            "description": self.description,
            "activities": self.activities,
            "contact": self.contact,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NGO":
        """Создание объекта из словаря"""
        return cls(
            user_id=data.get("user_id"),
            ngo_name=data.get("ngo_name"),
            description=data.get("description"),
            activities=data.get("activities"),
            contact=data.get("contact"),
            is_active=data.get("is_active", True),
        )
