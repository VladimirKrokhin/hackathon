from dataclasses import dataclass, field
from enum import StrEnum, auto
from pathlib import Path
from typing import Optional, Mapping, Any


@dataclass(frozen=True)
class Dimensions:
    width: int
    height: int


@dataclass(frozen=True)
class EventData:
    timestamp: str
    location: str
    audience: str


@dataclass(frozen=True)
class NgoData:
    name: str


@dataclass(frozen=True)
class CardData:
    image_path: Path
    title: str
    ngo_data: Optional[NgoData]
    event_data: Optional[EventData]


class CardTemplate(StrEnum):
    TELEGRAM = auto()
    VK = auto()
    WEBSITE = auto()


@dataclass(frozen=True)
class RenderParameters:
    template: CardTemplate


@dataclass
class PromptContext:
    """
    Структура данных контекста для промптов генерации контента.

    Содержит всю информацию, необходимую для генерации контента социальных сетей,
    включая детали мероприятий, информацию об НКО, требования платформы
    и предпочтения стиля повествования.

    Attributes:
        goal (str): Цель создания контента
        audience (list[str]): Целевая аудитория
        platform (str): Платформа публикации
        content_format (list[str]): Формат контента
        volume (str): Объем контента
        event_details (dict[str, str]): Детали мероприятия
        has_event (bool): Наличие информации о мероприятии
        event_type (str): Тип мероприятия
        event_date (str): Дата мероприятия
        event_place (str): Место проведения
        event_audience (str): Целевая аудитория мероприятия
        narrative_style (str): Стиль повествования
        has_ngo_info (bool): Наличие информации об НКО
        ngo_name (str): Название НКО
        ngo_description (str): Описание НКО
        ngo_activities (str): Деятельность НКО
        ngo_contact (str): Контактная информация НКО
    """
    goal: str = ""
    audience: list[str] = field(default_factory=list)
    platform: str = ""
    content_format: list[str] = field(default_factory=list)
    volume: str = ""
    event_details: dict[str, str] = field(default_factory=dict)
    has_event: bool = False

    # Поля структурированной формы
    event_type: str = ""
    event_date: str = ""
    event_place: str = ""
    event_audience: str = ""
    narrative_style: str = ""

    # Информация об НКО
    has_ngo_info: bool = False
    ngo_name: str = ""
    ngo_description: str = ""
    ngo_activities: str = ""
    ngo_contact: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromptContext":
        """
        Создает экземпляр PromptContext из словарных данных.

        Args:
            data (Mapping[str, Any]): Словарь, содержащий данные контекста

        Returns:
            PromptContext: Новый экземпляр с данными из словаря
        """
        return cls(
            goal=data.get("goal", ""),
            audience=data.get("audience", []),
            platform=data.get("platform", ""),
            content_format=data.get("format", []),
            volume=data.get("volume", ""),
            event_details=data.get("event_details", {}),
            has_event=bool(data.get("has_event", False)),
            # Структурированные поля
            event_type=data.get("event_type", ""),
            event_date=data.get("event_date", ""),
            event_place=data.get("event_place", ""),
            event_audience=data.get("event_audience", ""),
            narrative_style=data.get("narrative_style", ""),
            # Информация об НКО
            has_ngo_info=bool(data.get("has_ngo_info", False)),
            ngo_name=data.get("ngo_name", ""),
            ngo_description=data.get("ngo_description", ""),
            ngo_activities=data.get("ngo_activities", ""),
            ngo_contact=data.get("ngo_contact", ""),
        )


@dataclass
class PlanPromptContext:
    """
    Структура данных контекста для промптов планирования контента.

    Содержит информацию, необходимую для создания контент-планов, включая
    временные периоды, частоту публикаций, темы и дополнительные требования.

    Attributes:
        period (str): Период планирования
        frequency (str): Частота публикаций
        themes (str): Темы контента
        details (str): Дополнительные детали
    """
    period: str = ""
    frequency: str = ""
    themes: str = ""
    details: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanPromptContext":
        """
        Создает экземпляр PlanPromptContext из словарных данных.

        Args:
            data (Mapping[str, Any]): Словарь, содержащий данные контекста плана

        Returns:
            PlanPromptContext: Новый экземпляр с данными из словаря
        """
        return cls(
            period=data["period"],
            frequency=data["frequency"],
            themes=data["themes"],
            details=data["details"],
        )


@dataclass
class EditPromptContext:
    """
    Структура данных контекста для промптов редактирования текста.

    Содержит текст для редактирования вместе с дополнительным контекстом,
    включая информацию об НКО, которая может быть релевантной для процесса редактирования.

    Attributes:
        text_to_edit (str): Текст для редактирования
        details (str): Дополнительные детали
        has_ngo_info (bool): Наличие информации об НКО
        ngo_name (str): Название НКО
        ngo_description (str): Описание НКО
        ngo_activities (str): Деятельность НКО
        ngo_contact (str): Контактная информация НКО
    """
    text_to_edit: str = ""
    details: str = ""
    # Информация об НКО
    has_ngo_info: bool = False
    ngo_name: str = ""
    ngo_description: str = ""
    ngo_activities: str = ""
    ngo_contact: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EditPromptContext":
        """
        Создает экземпляр EditPromptContext из словарных данных.

        Args:
            data (Mapping[str, Any]): Словарь, содержащий данные контекста редактирования

        Returns:
            EditPromptContext: Новый экземпляр с данными из словаря
        """
        return cls(
            text_to_edit=data["text_to_edit"],
            details=data.get("details", ""),
            # Информация об НКО
            has_ngo_info=bool(data.get("has_ngo_info", False)),
            ngo_name=data.get("ngo_name", ""),
            ngo_description=data.get("ngo_description", ""),
            ngo_activities=data.get("ngo_activities", ""),
            ngo_contact=data.get("ngo_contact", ""),
        )
