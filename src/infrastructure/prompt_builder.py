from abc import ABC, abstractmethod
from typing import Dict, Union


import logging
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Union

logger = logging.getLogger(__name__)


@dataclass
class PromptContext:
    goal: str = ""
    audience: list[str] = field(default_factory=list)
    platform: str = ""
    content_format: list[str] = field(default_factory=list)
    volume: str = ""
    event_details: dict[str, str] = field(default_factory=dict)
    has_event: bool = False
    
    # Информация об НКО
    has_ngo_info: bool = False
    ngo_name: str = ""
    ngo_description: str = ""
    ngo_activities: str = ""
    ngo_contact: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromptContext":
        return cls(
            goal=data.get("goal", ""),
            audience=data.get("audience", []),
            platform=data.get("platform", ""),
            content_format=data.get("format", []),
            volume=data.get("volume", ""),
            event_details=data.get("event_details", {}),
            has_event=bool(data.get("has_event", False)),
            has_ngo_info=bool(data.get("has_ngo_info", False)),
            ngo_name=data.get("ngo_name", ""),
            ngo_description=data.get("ngo_description", ""),
            ngo_activities=data.get("ngo_activities", ""),
            ngo_contact=data.get("ngo_contact", ""),
        )


@dataclass
class PlanPromptContext:
    period: str = ""
    frequency: str = ""
    themes: str = ""
    details: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanPromptContext":
        return cls(
            period=data.get("period", ""),
            frequency=data.get("frequency", ""),
            themes=data.get("themes", ""),
            details=data.get("details", ""),
        )


@dataclass
class EditPromptContext:
    text_to_edit: str = ""
    details: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EditPromptContext":
        return cls(
            text_to_edit=data.get("text_to_edit", ""),
            details=data.get("details", ""),
        )


class AbstractPromptBuilder(ABC):
    @abstractmethod
    def build_text_content_prompt(self, user_data: PromptContext, user_text: str) -> str:
        pass

    @abstractmethod
    def build_refactor_text_content_prompt(self, user_data: PromptContext, generated_post: str, user_text: str) -> str:
        pass


class YandexGPTPromptBuilder(AbstractPromptBuilder):

    def build_text_content_prompt(self, user_data: PromptContext, user_text: str) -> str:

        goal = user_data.goal
        audience_list = self._normalize_to_list(user_data.audience)
        audience = ", ".join(audience_list)
        platform = user_data.platform
        content_format = ", ".join(
            self._normalize_to_list(user_data.content_format)
        )
        volume = user_data.volume
        event_details = user_data.event_details or ""
        has_event = bool(user_data.has_event)
        
        # Информация об НКО
        has_ngo_info = bool(user_data.has_ngo_info)
        ngo_name = user_data.ngo_name
        ngo_description = user_data.ngo_description
        ngo_activities = user_data.ngo_activities
        ngo_contact = user_data.ngo_contact

        audience_style = self._get_audience_style(audience_list)
        platform_requirements = self._get_platform_requirements(platform)

        sections = [
            "Выступай как профессиональный SMM-менеджер НКО.",
            "Подготовь пост в соответствии с данными параметрами:",
            f"• Цель: {goal}",
            f"• Целевая аудитория: {audience}",
            f"• Платформа: {platform} ({platform_requirements})",
            f"• Формат: {content_format}",
            f"• Объем: {volume}",
            f"• Стиль и тон: {audience_style}",
        ]
        
        # Добавляем информацию об НКО, если она есть
        if has_ngo_info and ngo_name:
            sections.extend([
                "Информация о НКО:",
                f"• Название: {ngo_name}",
            ])
            if ngo_description and ngo_description != "Не указано":
                sections.append(f"• Описание: {ngo_description}")
            if ngo_activities and ngo_activities != "Не указано":
                sections.append(f"• Деятельность: {ngo_activities}")
            if ngo_contact and ngo_contact != "Не указано":
                sections.append(f"• Контакты: {ngo_contact}")
            sections.append("Обязательно используй эту информацию при создании поста.")
        
        sections.extend([
            "Дополнительные требования:",
            "• Не упоминай режимные объекты, безопасность, военные базы или ограничения на передвижение.",
            "• Фокусируйся на социальной миссии и помощи людям.",
            "• Обязательно добавь контакты для связи и призыв к конкретному действию.",
        ])

        if has_event and event_details:
            sections.append("Контекст мероприятия:")
            sections.append(self._format_event_details(event_details))

        if user_text:
            sections.append("Информация от пользователя:")
            sections.append(user_text.strip())

        sections.append("Примеры удачных постов для вдохновения:")
        sections.extend(
            [
                '• "🌟 Друзья, нам нужны волонтеры! Помогите детям из многодетных семей подготовиться к школе. Ваше участие изменит жизни этих детей!"',
                '• "💡 Ваша поддержка важна! Благодаря вам мы собрали 100 комплектов школьных принадлежностей для детей нашего города."',
                '• "Приглашаем на благотворительный концерт! 15 декабря в ДК «Родина». Все средства пойдут на ремонт детской площадки."',
            ]
        )

        sections.append(
            "Ответь только готовым текстом поста, без дополнительных комментариев и пояснений."
        )

        prompt = "\n".join(sections)
        return textwrap.dedent(prompt).strip()

    def build_refactor_text_content_prompt(self, user_data: PromptContext, generated_post: str, user_text: str) -> str:
        goal = user_data.goal
        audience_list = self._normalize_to_list(user_data.audience)
        audience = ", ".join(audience_list)
        platform = user_data.platform
        content_format = ", ".join(
            self._normalize_to_list(user_data.content_format)
        )
        volume = user_data.volume
        event_details = user_data.event_details or ""
        has_event = bool(user_data.has_event)
        
        # Информация об НКО
        has_ngo_info = bool(user_data.has_ngo_info)
        ngo_name = user_data.ngo_name
        ngo_description = user_data.ngo_description
        ngo_activities = user_data.ngo_activities
        ngo_contact = user_data.ngo_contact

        audience_style = self._get_audience_style(audience_list)
        platform_requirements = self._get_platform_requirements(platform)

        sections = [
            "Выступай как профессиональный SMM-менеджер НКО.",
            f"Отредактируй пост в соответствии с данной просьбой: {user_text}",
            "Общие данные о посте:",
            f"• Цель: {goal}",
            f"• Целевая аудитория: {audience}",
            f"• Платформа: {platform} ({platform_requirements})",
            f"• Формат: {content_format}",
            f"• Объем: {volume}",
            f"• Стиль и тон: {audience_style}",
        ]
        
        # Добавляем информацию об НКО, если она есть
        if has_ngo_info and ngo_name:
            sections.extend([
                "Информация о НКО:",
                f"• Название: {ngo_name}",
            ])
            if ngo_description and ngo_description != "Не указано":
                sections.append(f"• Описание: {ngo_description}")
            if ngo_activities and ngo_activities != "Не указано":
                sections.append(f"• Деятельность: {ngo_activities}")
            if ngo_contact and ngo_contact != "Не указано":
                sections.append(f"• Контакты: {ngo_contact}")
            sections.append("Обязательно используй эту информацию при редактировании поста.")

        if has_event and event_details:
            sections.append("Контекст мероприятия:")
            sections.append(self._format_event_details(event_details))

        sections.extend([
            "Дополнительные требования:",
            "• Не упоминай режимные объекты, безопасность, военные базы или ограничения на передвижение.",
            "• Фокусируйся на социальной миссии и помощи людям.",
            "• Обязательно добавь контакты для связи и призыв к конкретному действию.",
        ])

        sections.append("Вот пост, который нужно отредактировать:")
        sections.append(generated_post)

        sections.append(
            "Ответь только готовым текстом отредактированного поста, без дополнительных комментариев и пояснений."
        )
        prompt = "\n".join(sections)
        return textwrap.dedent(prompt).strip()

    def build_content_plan_prompt(self, user_data: PlanPromptContext) -> str:

        period = user_data.period
        frequency = user_data.frequency
        themes = user_data.themes
        details = user_data.details

        sections = [
            "Задача: составь контент-план для канала НКО в соцсети. Укажи дни и категории постов.",
            "Контекст для создания:",
            f"• Период: {period}",
            f"• Частота публикаций: {frequency}",
            f"• Темы: {themes}",
        ]

        if details:
            sections.append(f"• Особые требования: {details}")

        sections.extend([
            "Также давай пояснения почему ты предложил именно такой план.",
            "Используй отступы, списки и эмодзи для лучшей читаемости. Не перегружай текст.",
            "Используй оформление текста, которое корректно отображается в Telegram.",
        ])

        prompt = "\n".join(sections)
        return textwrap.dedent(prompt).strip()

    def build_edit_text_prompt(self, user_data: EditPromptContext) -> str:
        text_to_edit = user_data.text_to_edit
        details = user_data.details

        sections = [
            "Задача: отредактируй текст по грамматике, орфографии, логике и стилю. ",
            "Старайся сохранять основную тему исходного текста."
            "Покажи исправленный вариант и перечисли, какие ошибки были и как их исправили.",
            f"Исходный текст: {text_to_edit}",
        ]

        if details:
            sections.append(f"Дополнительные детали, которые нужно учитывать при редактировании текста: {details}")

        prompt = "\n".join(sections)
        return textwrap.dedent(prompt).strip()

    @staticmethod
    def _normalize_to_list(value: Union[str, Iterable[str]]) -> List[str]:
        """
        Приводит значение к списку строк. Игнорирует None.
        """
        if value is None:
            return []
        if isinstance(value, str):
            value = value.strip()
            return [value] if value else []
        if isinstance(value, Iterable):
            result = []
            for item in value:
                if item is None:
                    continue
                if isinstance(item, str):
                    item = item.strip()
                    if item:
                        result.append(item)
                else:
                    result.append(str(item))
            return result
        return [str(value)]

    @staticmethod
    def _get_audience_style(audience: List[str]) -> str:
        """Определение стиля текста на основе аудитории"""
        audience_lower = ", ".join(audience).lower()

        if any(key in audience_lower for key in ("молодежь", "14-25", "студенты")):
            return "неформальный, энергичный, с эмодзи в начале абзацев, современный сленг"
        if any(key in audience_lower for key in ("семьи с детьми", "родители")):
            return "теплый, заботливый, без жаргона, с акцентом на семейные ценности"
        if any(key in audience_lower for key in ("бизнес", "организации", "компании")):
            return (
                "профессиональный, с акцентом на социальную ответственность и измеримые результаты"
            )
        if any(key in audience_lower for key in ("пожилые", "45+", "старшее поколение")):
            return "уважительный, понятный, без сложных терминов, с акцентом на традиции и заботу"
        return "универсальный, дружелюбный, но профессиональный"

    @staticmethod
    def _get_platform_requirements(platform: str) -> str:
        platform_lower = platform.lower()

        if any(key in platform_lower for key in ("вконтакте", "vk", "вк")):
            return (
                "3–5 эмодзи в тексте, 3–5 релевантных хештегов в конце, короткие абзацы (1–2 предложения)"
            )
        if any(key in platform_lower for key in ("telegram", "телеграм", "tg")):
            return (
                "используй **жирный** для заголовков, --- для разделителей, 1–2 ключевых хештега, минимум эмодзи"
            )
        if any(key in platform_lower for key in ("сайт", "рассылка", "newsletter")):
            return "официальный стиль, полные предложения, без эмодзи"
        return "универсальные требования для соцсетей"

    @staticmethod
    def _format_event_details(event_details: Union[str, Dict]) -> str:
        if isinstance(event_details, dict):
            parts = []
            for key, value in event_details.items():
                if value:
                    parts.append(f"{key.capitalize()}: {value}")
            event_text = "; ".join(parts)
        else:
            event_text = str(event_details).strip()

        template = textwrap.dedent(
            """
            • Укажи точную дату и время.
            • Укажи место проведения (без упоминания режимных зон).
            • Объясни, зачем нужно это мероприятие и что будет интересного.
            • Расскажи, что получат участники.
            • Добавь срочный призыв к регистрации, если есть дедлайн.
            """
        ).strip()

        return f"{event_text}\n{template}"
