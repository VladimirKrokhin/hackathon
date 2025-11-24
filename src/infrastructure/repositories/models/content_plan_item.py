"""
Модель данных для элементов контент-планов (отдельных публикаций)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from . import Base


class PublicationStatus(enum.Enum):
    """Статусы публикации"""
    SCHEDULED = "запланировано"
    PUBLISHED = "опубликовано"
    OVERDUE = "просрочено"


class ContentPlanItem(Base):
    """
    Модель для хранения элементов контент-плана (отдельных публикаций)
    """
    __tablename__ = "content_plan_items"

    id = Column(Integer, primary_key=True, index=True)
    content_plan_id = Column(Integer, ForeignKey("content_plans.id"), nullable=False, comment="ID контент-плана")
    
    # Информация о публикации
    publication_date = Column(DateTime(timezone=True), nullable=False, comment="Дата и время публикации")
    content_title = Column(String(255), nullable=False, comment="Заголовок контента")
    content_text = Column(Text, nullable=True, comment="Текст контента для публикации")
    
    # Статус и уведомления
    status = Column(SQLEnum(PublicationStatus), default=PublicationStatus.SCHEDULED, comment="Статус публикации")
    notification_sent = Column(Boolean, default=False, comment="Отправлено ли уведомление")
    notification_sent_at = Column(DateTime(timezone=True), nullable=True, comment="Когда отправлено уведомление")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Дата создания")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Дата обновления")
    
    # Связь с контент-планом
    content_plan = relationship("ContentPlan", back_populates="items")
    
    def __repr__(self) -> str:
        return f"<ContentPlanItem(id={self.id}, plan_id={self.content_plan_id}, title='{self.content_title}')>"
    
    def to_dict(self) -> dict:
        """Преобразование модели в словарь для удобства использования"""
        return {
            "id": self.id,
            "content_plan_id": self.content_plan_id,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "content_title": self.content_title,
            "content_text": self.content_text,
            "status": self.status.value if self.status else None,
            "notification_sent": self.notification_sent,
            "notification_sent_at": self.notification_sent_at.isoformat() if self.notification_sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ContentPlanItem":
        """Создание объекта из словаря"""
        status_value = data.get("status")
        status = PublicationStatus(status_value) if status_value else PublicationStatus.SCHEDULED
        
        return cls(
            content_plan_id=data.get("content_plan_id"),
            publication_date=data.get("publication_date"),
            content_title=data.get("content_title"),
            content_text=data.get("content_text"),
            status=status,
            notification_sent=data.get("notification_sent", False),
        )
