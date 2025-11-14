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

generation_router = Router(name="generation")


logger = logging.getLogger(__name__)


@generation_router.message(ContentGeneration.waiting_for_user_text, F.text)
async def user_text_handler(message: Message, state: FSMContext):
    user_text = message.text.strip()
    await state.update_data(user_text=user_text)
    data = await state.get_data()

    goal = data.get("goal", "🎯 Привлечь волонтеров")
    platform = data.get("platform", "выбранной платформы")
    audience = data.get("audience", [])
    generated_post = None

    await message.answer("🧠 Генерирую контент с помощью YandexGPT...", reply_markup=ReplyKeyboardRemove())

    try:
        generated_post = await dp["content_generation_service"].generate_text_content(data, user_text)
        await state.update_data(generated_post=generated_post)
    except Exception as error:
        logger.exception("Ошибка при генерации текста: %s", error)
        await message.answer(
            "⚠️ Не удалось получить ответ."
        )
        raise error

    await message.answer(
        f"✅ Ваш сгенерированный контент:",
    )
    await message.answer(generated_post, parse_mode=ParseMode.MARKDOWN)

    await message.answer("🎨 Создаю информационные карточки...")

    try:
        template_data = {
            "title": get_title_by_goal(goal),
            "subtitle": f"Для {', '.join(audience or ['наших подопечных'])}",
            "content": f"{generated_post[:250]}..." if len(generated_post) > 250 else generated_post,
            "org_name": data.get("org_name", "Ваша НКО"),
            "contact_info": data.get("contact_info", "тел: +7 (XXX) XXX-XX-XX"),
            "primary_color": get_color_by_goal(goal),
            "secondary_color": get_secondary_color_by_goal(goal),
            "text_color": "#333333",
            "background_color": "#f5f7fa",
        }

        template_name = get_template_by_platform(platform)
        cards = await dp["card_generation_service"].generate_multiple_cards(
            template_name=template_name,
            data=template_data,
            platform=platform,
        )

        if not cards:
            raise ValueError("Генератор карточек ничего не вернул")

        await message.answer("🎨 Вот ваши карточки для соцсетей:")

        for card_type, image_bytes in cards.items():
            caption = get_caption_for_card_type(card_type, platform)
            image_stream = image_bytes
            await message.answer_photo(
                photo=BufferedInputFile(image_stream, f"{card_type}.png"),
                caption=caption,
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
        )
        raise error