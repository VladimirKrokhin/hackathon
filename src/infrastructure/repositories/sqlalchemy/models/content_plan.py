"""
Модель данных для контент-планов
"""
from datetime import datetime
from typing import Iterable

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped

from models import ContentPlan
from . import Base
from .content_plan_item import SqlAlchemyContentPlanItemModel


class SqlAlchemyContentPlanModel(Base):
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
    topics = Column(Text, nullable=False, comment="Темы для контента")
    details = Column(Text, nullable=True, comment="Дополнительные детали и требования")
    
    # Сгенерированный контент-план
    plan_data = Column(JSON, nullable=False, comment="JSON с структурированными данными плана")
    
    # Статус плана
    is_active = Column(Boolean, default=True, comment="Активен ли план")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Дата создания")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Дата обновления")
    
    # Связанные элементы плана
    items = relationship("SqlAlchemyContentPlanItemModel", back_populates="content_plan", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<ContentPlan(id={self.id}, user_id={self.user_id}, name='{self.plan_name}')>"


    def to_domain_model(self) -> ContentPlan:
        dto = ContentPlan(
            id_=self.id,
            user_id=self.user_id,
            plan_name=self.plan_name,
            period=self.period,
            frequency=self.frequency,
            topics=self.topics,
            details=self.details,
            plan_data=self.plan_data, # FIXME!!!
            items=tuple(item.to_domain_model() for item in self.items)
        )
        return dto
    

    @classmethod
    def from_domain_model(cls, dto: ContentPlan) -> "SqlAlchemyContentPlanModel":
        return cls(
            id=dto.id_,
            user_id=dto.user_id,
            plan_name=dto.plan_name,
            period=dto.period,
            frequency=dto.frequency,
            topics=dto.topics,
            details=dto.details,
            plan_data=dto.plan_data,
            items=[SqlAlchemyContentPlanItemModel.from_domain_model(item_dto) for item_dto in dto.items]
        )
