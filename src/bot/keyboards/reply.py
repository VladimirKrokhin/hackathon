from typing import List, Optional

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

GOAL_OPTIONS = [
    "🎯 Привлечь волонтеров",
    "💰 Найти спонсоров/доноров",
    "📢 Рассказать о мероприятии",
    "❤️ Повысить осведомленность о проблеме",
    "🤝 Укрепить отношения со сторонниками",
]

AUDIENCE_OPTIONS = [
    "👨‍🎓 Молодежь (14-25 лет)",
    "👨‍👩‍👧‍👦 Семьи с детьми",
    "💼 Работающие взрослые (25-45 лет)",
    "👴 Люди старшего возраста (45+)",
    "🏢 Бизнес/организации",
]

PLATFORM_OPTIONS = [
    "📱 ВКонтакте (для молодежи)",
    "💬 Telegram (для взрослых/бизнеса)",
    "📸 Instagram (визуальный контент)",
]

FORMAT_OPTIONS = [
    "📝 Информационный пост (70% контента)",
    "🎭 Развлекательный/эмоциональный пост (20%)",
    "💬 Пост для вовлечения аудитории (10%)",
    "📅 Напоминание о мероприятии",
]

VOLUME_OPTIONS = [
    "📱 Короткий пост (1-3 предложения + карточка)",
    "📝 Средний пост (3-5 предложений + 2-3 карточки)",
    "📖 Развернутый пост (5+ предложений + 4-5 карточек)",
]

# Content plan keyboards
PERIOD_OPTIONS = [
    "3 дня",
    "Неделя",
    "Месяц",
]

FREQUENCY_OPTIONS = [
    "каждый день",
    "раз в два дня",
]

CUSTOM_OPTION = "🖊️ Свой вариант"

YES_NO_OPTIONS = ["✅ Да", "❌ Нет"]

DONE_OPTION = "✅ Готово"
SKIP_OPTION = "Пропустить"


def _build_keyboard(rows: List[List[str]], *, resize: bool = True, one_time: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=button_text) for button_text in row]
        for row in rows
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=resize,
        one_time_keyboard=one_time,
    )


def get_goal_keyboard() -> ReplyKeyboardMarkup:
    return _build_keyboard([[option] for option in GOAL_OPTIONS], one_time=True)


def get_audience_keyboard(selected: Optional[List[str]] = None) -> ReplyKeyboardMarkup:
    rows = [[option] for option in AUDIENCE_OPTIONS]
    rows.append([DONE_OPTION])
    return _build_keyboard(rows)


def get_platform_keyboard() -> ReplyKeyboardMarkup:
    return _build_keyboard([[option] for option in PLATFORM_OPTIONS], one_time=True)


def get_format_keyboard(selected: Optional[List[str]] = None) -> ReplyKeyboardMarkup:
    rows = [[option] for option in FORMAT_OPTIONS]
    rows.append([DONE_OPTION])
    return _build_keyboard(rows)


def get_volume_keyboard() -> ReplyKeyboardMarkup:
    return _build_keyboard([[option] for option in VOLUME_OPTIONS], one_time=True)


def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    return _build_keyboard([[YES_NO_OPTIONS[0]], [YES_NO_OPTIONS[1]]], one_time=True)


def get_skip_keyboard(label: str = SKIP_OPTION) -> ReplyKeyboardMarkup:
    return _build_keyboard([[label]], one_time=True)


NGO_MAIN_OPTIONS = [
    "🏢 Заполнить информацию об НКО",
    "✨ Создать контент без НКО",
    "📋 Посмотреть мою НКО",
    "🔄 Обновить данные НКО",
]

NGO_NAVIGATION_OPTIONS = [
    "❌ Отмена",
    "⏩ Пропустить",
    "✅ Готово",
]


def get_ngo_main_keyboard() -> ReplyKeyboardMarkup:
    rows = [[option] for option in NGO_MAIN_OPTIONS]
    return _build_keyboard(rows, one_time=True)


def get_ngo_navigation_keyboard() -> ReplyKeyboardMarkup:
    rows = [[option] for option in NGO_NAVIGATION_OPTIONS]
    return _build_keyboard(rows)


def get_example_keyboard(example: str) -> ReplyKeyboardMarkup:
    return _build_keyboard([[example]], one_time=True)


def get_period_keyboard() -> ReplyKeyboardMarkup:
    rows = [[option] for option in PERIOD_OPTIONS]
    rows.append([CUSTOM_OPTION])
    return _build_keyboard(rows)


def get_frequency_keyboard() -> ReplyKeyboardMarkup:
    rows = [[option] for option in FREQUENCY_OPTIONS]
    rows.append([CUSTOM_OPTION])
    return _build_keyboard(rows)
