import logging

from aiogram import Router, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.states import ContentGeneration
from bot.keyboards.inline import (
    get_narrative_style_keyboard,
    get_platform_keyboard,
    get_yes_no_keyboard,
)

logger = logging.getLogger(__name__)

new_generation_router = Router(name="new_generation")


@new_generation_router.message(ContentGeneration.waiting_for_ngo_info_choice, F.text)
async def ngo_info_choice_handler(message: Message, state: FSMContext):
    """Обработчик выбора использования данных НКО."""
    answer = message.text.strip()
    
    if answer not in ["✅ Да", "❌ Нет"]:
        await message.answer(
            "Пожалуйста, используйте кнопки «Да» или «Нет».",
            reply_markup=get_yes_no_keyboard(),
        )
        return

    has_ngo = answer == "✅ Да"
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "structured")

    if has_ngo:
        # Получаем данные НКО из БД
        from app import dp
        ngo_service = dp["ngo_service"]
        user_id = message.from_user.id
        ngo_data = ngo_service.get_ngo_data(user_id)
        
        if ngo_data:
            await state.update_data(
                has_ngo_info=True,
                ngo_name=ngo_data.get("ngo_name", ""),
                ngo_description=ngo_data.get("ngo_description", ""),
                ngo_activities=ngo_data.get("ngo_activities", ""),
                ngo_contact=ngo_data.get("ngo_contact", ""),
            )
        else:
            await message.answer(
                "⚠️ Данные НКО не найдены. Продолжаем без данных НКО.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.update_data(has_ngo_info=False)
    else:
        await state.update_data(has_ngo_info=False)

    # Переходим к соответствующему режиму
    if generation_mode == "structured":
        await message.answer(
            "📝 Отлично! Начинаем структурированную форму.\n\n"
            "**Что за событие?**\n"
            "Опишите коротко, о каком событии будет пост.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_event_type)
    else:  # free_form
        await message.answer(
            "💭 Понятно! Используем свободную форму.\n\n"
            "**Опишите ваш пост**\n"
            "Расскажите подробно, о чём будет пост, какую информацию нужно донести.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_user_description)


# ===============================
# СТРУКТУРИРОВАННАЯ ФОРМА
# ===============================

@new_generation_router.message(ContentGeneration.waiting_for_event_type, F.text)
async def event_type_handler(message: Message, state: FSMContext):
    """Обработчик для типа события."""
    event_type = message.text.strip()
    if not event_type:
        await message.answer(
            "Пожалуйста, опишите событие.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(event_type=event_type)
    
    await message.answer(
        "📅 **Когда состоится событие?**\n"
        "Укажите дату и время проведения.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_event_date)


@new_generation_router.message(ContentGeneration.waiting_for_event_date, F.text)
async def event_date_handler(message: Message, state: FSMContext):
    """Обработчик для даты события."""
    event_date = message.text.strip()
    if not event_date:
        await message.answer(
            "Пожалуйста, укажите дату и время.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(event_date=event_date)
    
    await message.answer(
        "📍 **Где состоится событие?**\n"
        "Укажите место проведения.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_event_place)


@new_generation_router.message(ContentGeneration.waiting_for_event_place, F.text)
async def event_place_handler(message: Message, state: FSMContext):
    """Обработчик для места события."""
    event_place = message.text.strip()
    if not event_place:
        await message.answer(
            "Пожалуйста, укажите место проведения.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(event_place=event_place)
    
    await message.answer(
        "👥 **Кто приглашен на событие?**\n"
        "Укажите целевую аудиторию (например: волонтеры, дети, родители, пенсионеры).",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_event_audience)


@new_generation_router.message(ContentGeneration.waiting_for_event_audience, F.text)
async def event_audience_handler(message: Message, state: FSMContext):
    """Обработчик для аудитории события."""
    event_audience = message.text.strip()
    if not event_audience:
        await message.answer(
            "Пожалуйста, укажите целевую аудиторию.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(event_audience=event_audience)
    
    await message.answer(
        "📝 **Дополнительные детали**\n"
        "Расскажите подробнее о событии: что будет интересного, зачем нужно участие, какая польза для участников.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_event_details)


@new_generation_router.message(ContentGeneration.waiting_for_event_details, F.text)
async def event_details_handler(message: Message, state: FSMContext):
    """Обработчик для дополнительных деталей события."""
    event_details = message.text.strip()
    
    await state.update_data(event_details=event_details)
    
    await message.answer(
        "🎨 **Выберите стиль повествования поста**",
        reply_markup=get_narrative_style_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_narrative_style)


@new_generation_router.message(ContentGeneration.waiting_for_narrative_style, F.text)
async def narrative_style_handler(message: Message, state: FSMContext):
    """Обработчик для стиля повествования."""
    style = message.text.strip()
    
    narrative_styles = [
        "💬 Разговорный стиль",
        "📋 Официально-деловой стиль", 
        "🎨 Художественный стиль",
        "🌟 Позитивный/мотивирующий стиль",
    ]
    
    if style not in narrative_styles:
        await message.answer(
            "Пожалуйста, выберите стиль из списка.",
            reply_markup=get_narrative_style_keyboard(),
        )
        return

    await state.update_data(narrative_style=style)
    
    await message.answer(
        "📱 **На какой платформе будет публиковаться пост?**",
        reply_markup=get_platform_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_platform)


@new_generation_router.message(ContentGeneration.waiting_for_platform, F.text)
async def platform_handler(message: Message, state: FSMContext):
    """Обработчик для выбора платформы - завершение структурированной формы."""
    platform = message.text.strip()
    
    platform_options = [
        "📱 ВКонтакте (для молодежи)",
        "💬 Telegram (для взрослых/бизнеса)",
        "📸 Instagram (визуальный контент)",
    ]
    
    if platform not in platform_options:
        await message.answer(
            "Пожалуйста, выберите платформу из списка.",
            reply_markup=get_platform_keyboard(),
        )
        return

    await state.update_data(platform=platform)
    
    # Получаем все данные и переходим к генерации
    data = await state.get_data()
    data["user_text"] = f"Структурированная форма: {data.get('event_type', '')}"
    
    # Импортируем и вызываем генерацию
    from bot.handlers.generation import complete_generation_handler
    await complete_generation_handler(message, state)


# ===============================
# СВОБОДНАЯ ФОРМА
# ===============================

@new_generation_router.message(ContentGeneration.waiting_for_user_description, F.text)
async def user_description_handler(message: Message, state: FSMContext):
    """Обработчик для описания пользователя в свободной форме."""
    user_description = message.text.strip()
    if not user_description:
        await message.answer(
            "Пожалуйста, опишите ваш пост.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(user_text=user_description)
    
    await message.answer(
        "🎨 **Выберите стиль повествования поста**",
        reply_markup=get_narrative_style_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_free_style)


@new_generation_router.message(ContentGeneration.waiting_for_free_style, F.text)
async def free_style_handler(message: Message, state: FSMContext):
    """Обработчик для стиля повествования в свободной форме."""
    style = message.text.strip()
    
    narrative_styles = [
        "💬 Разговорный стиль",
        "📋 Официально-деловой стиль", 
        "🎨 Художественный стиль",
        "🌟 Позитивный/мотивирующий стиль",
    ]
    
    if style not in narrative_styles:
        await message.answer(
            "Пожалуйста, выберите стиль из списка.",
            reply_markup=get_narrative_style_keyboard(),
        )
        return

    await state.update_data(narrative_style=style)
    
    await message.answer(
        "📱 **На какой платформе будет публиковаться пост?**",
        reply_markup=get_platform_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_platform)
