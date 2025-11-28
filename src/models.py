from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Optional


@dataclass
class Ngo:
    """Информация о НКО."""
    id_: Optional[int]
    user_id: int
    name: str
    description: str
    activities: str
    contacts: str


class PublicationStatus(StrEnum):
    """Статусы публикации"""
    SCHEDULED = "запланировано"
    PUBLISHED = "опубликовано"
    OVERDUE = "просрочено"

@dataclass
class ContentPlanItem:
    """Элемент контент-плана."""
    id_: Optional[int]
    content_plan_id: int

    # Информация о публикации
    publication_date: datetime
    content_title: str
    content_text: str

    # Статус
    status: PublicationStatus
    notification_sent: bool
    notification_sent_at: datetime

@dataclass
class ContentPlan:
    """Запись в контент-плане."""
    id_: Optional[int]
    user_id: int
    plan_name: str
    period: str
    frequency: str
    topics: str
    details: str

    # Сгенерированный контент-план
    plan_data: dict = field(default_factory=dict)

    # Связанные элементы плана
    items: tuple[ContentPlanItem] = field(default_factory=tuple)


