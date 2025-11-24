"""
Модель данных для контент-планов
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base


class ContentPlan(Base):
    """
    Модель для хранения контент-планов пользователей
    """
    __tablename__ = "content_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False, comment="ID пользователя Telegram")
    
    # Основная информация о плане
    plan_name = Column(String(255), nullable=False, comment="Название контент-плана")
    period = Column(String(50), nullable=False, comment="Период плана (3 дня, неделя, месяц)")
    frequency = Column(String(50), nullable=False, comment="Частота публикаций")
    themes = Column(Text, nullable=False, comment="Темы для контента")
    details = Column(Text, nullable=True, comment="Дополнительные детали и требования")
    
    # Сгенерированный контент-план
    plan_data = Column(JSON, nullable=False, comment="JSON с структурированными данными плана")
    
    # Статус плана
    is_active = Column(Boolean, default=True, comment="Активен ли план")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Дата создания")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Дата обновления")
    
    # Связанные элементы плана
    items = relationship("ContentPlanItem", back_populates="content_plan", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<ContentPlan(id={self.id}, user_id={self.user_id}, name='{self.plan_name}')>"
    
    def to_dict(self) -> dict:
        """Преобразование модели в словарь для удобства использования"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan_name": self.plan_name,
            "period": self.period,
            "frequency": self.frequency,
            "themes": self.themes,
            "details": self.details,
            "plan_data": self.plan_data,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ContentPlan":
        """Создание объекта из словаря"""
        return cls(
            user_id=data.get("user_id"),
            plan_name=data.get("plan_name"),
            period=data.get("period"),
            frequency=data.get("frequency"),
            themes=data.get("themes"),
            details=data.get("details"),
            plan_data=data.get("plan_data"),
            is_active=data.get("is_active", True),
        )
