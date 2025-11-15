import io
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.enums.parse_mode import ParseMode
from aiogram.types.input_file import BufferedInputFile

from app import dp
from bot.states import ContentGeneration
from bot.keyboards.inline import get_post_generation_keyboard
from bot.utils import (
    get_caption_for_card_type,
    get_color_by_goal,
    get_secondary_color_by_goal,
    get_template_by_platform,
    get_title_by_goal,
)
from services.content_generation import TextContentGenerationService
from services.card_generation import CardGenerationService

generation_router = Router(name="generation")

logger = logging.getLogger(__name__)


async def complete_generation_handler(message: Message, state: FSMContext):
    """Универсальная функция завершения генерации контента."""
    data = await state.get_data()
    user_text = data.get("user_text", "")
    
    # Определяем цель на основе данных
    goal = data.get("goal", "🎯 Рассказать о мероприятии")
    platform = data.get("platform", "📱 ВКонтакте (для молодежи)")
    
    # Получаем информацию об НКО из базы данных
    ngo_service = dp["ngo_service"]
    user_id = message.from_user.id
    ngo_data = ngo_service.get_ngo_data(user_id)
    
    # Обновляем данные пользователя информацией из БД
    if ngo_data:
        data.update(ngo_data)
    
    # Устанавливаем значения по умолчанию
    ngo_name = ngo_data.get("ngo_name", "Ваша НКО") if ngo_data else "Ваша НКО"
    ngo_contact = ngo_data.get("ngo_contact", "тел: +7 (XXX) XXX-XX-XX") if ngo_data else "тел: +7 (XXX) XXX-XX-XX"
    
    generated_post = None

    await message.answer(
        "🧠 Генерирую контент...",
        reply_markup=ReplyKeyboardRemove(),
        )

    try:
        text_generation_service: TextContentGenerationService = dp["text_content_generation_service"]
        generated_post = await text_generation_service.generate_text_content(data, user_text)
        await state.update_data(generated_post=generated_post)
    except Exception as error:
        logger.exception("Ошибка при генерации текста: %s", error)
        await message.answer(
            "⚠️ Не удалось получить ответ.",
            reply_markup=ReplyKeyboardRemove(),
        )
        raise error

    # Показываем сгенерированный пост
    await message.answer(
        f"✅ Ваш сгенерированный контент:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        generated_post,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
        )

    await message.answer(
        "🎨 Создаю информационные карточки...",
        reply_markup=ReplyKeyboardRemove(),
        )

    try:
        # Определяем подзаголовок в зависимости от режима
        if data.get("generation_mode") == "structured":
            subtitle = f"Событие: {data.get('event_type', 'мероприятие')}"
        else:
            subtitle = f"Для {data.get('event_audience', 'наших подопечных')}"
        
        template_data = {
            "title": get_title_by_goal(goal),
            "subtitle": subtitle,
            "content": f"{generated_post[:250]}..." if len(generated_post) > 250 else generated_post,
            "org_name": ngo_name,
            "contact_info": ngo_contact,
            "primary_color": get_color_by_goal(goal),
            "secondary_color": get_secondary_color_by_goal(goal),
            "text_color": "#333333",
            "background_color": "#f5f7fa",
        }

        template_name = get_template_by_platform(platform)
        card_generation_service: CardGenerationService = dp["card_generation_service"]

        cards = await card_generation_service.generate_multiple_cards(
            template_name=template_name,
            data=template_data,
            platform=platform,
        )

        if not cards:
            raise ValueError("Генератор карточек ничего не вернул")

        await message.answer(
            "🎨 Вот ваши карточки для соцсетей:",
            reply_markup=ReplyKeyboardRemove(),
            )

        for card_type, image_bytes in cards.items():
            caption = get_caption_for_card_type(card_type, platform)
            image_stream = image_bytes
            await message.answer_photo(
                photo=BufferedInputFile(image_stream, f"{card_type}.png"),
                caption=caption,
                reply_markup=ReplyKeyboardRemove(),
            )

        await message.answer(
            "✨ Все материалы готовы к публикации! Что хотите сделать дальше?",
            reply_markup=get_post_generation_keyboard(),
        )
        await state.set_state(ContentGeneration.waiting_for_confirmation)

    except Exception as error:
        logger.exception("Ошибка при генерации карточек: %s", error)
        await message.answer(
            "❌ Не удалось сформировать карточки.",
            reply_markup=ReplyKeyboardRemove(),
        )
        raise error


# @generation_router.message(ContentGeneration.waiting_for_user_text, F.text)
# async def user_text_handler(message: Message, state: FSMContext):
#     """Обработчик для старого режима генерации (совместимость)."""
#     user_text = message.text.strip()
#     await state.update_data(user_text=user_text)
#     await complete_generation_handler(message, state)
