"""
Модель данных для элементов контент-планов (отдельных публикаций)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from models import PublicationStatus, ContentPlanItem
from . import Base




class SqlAlchemyContentPlanItemModel(Base):
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
    content_plan = relationship("SqlAlchemyContentPlanModel", back_populates="items")
    
    def __repr__(self) -> str:
        return f"<ContentPlanItem(id={self.id}, plan_id={self.content_plan_id}, title='{self.content_title}')>"

    def to_domain_model(self) -> ContentPlanItem:
        dto = ContentPlanItem(
            id_=self.id,
            content_plan_id=self.content_plan_id,
            publication_date=self.publication_date,
            content_title=self.content_title,
            content_text=self.content_text,
            status=self.status,
            notification_sent=self.notification_sent,
            notification_sent_at=self.notification_sent_at,
        )

        return dto

    

    @classmethod
    def from_domain_model(cls, dto: ContentPlanItem) -> "SqlAlchemyContentPlanItemModel":

        return cls(
            id=dto.id_,
            content_plan_id=dto.content_plan_id,
            publication_date=dto.publication_date,
            content_title=dto.content_title,
            content_text=dto.content_text,
            status=dto.status,
            notification_sent=dto.notification_sent,
            notification_sent_at=dto.notification_sent_at,
        )
