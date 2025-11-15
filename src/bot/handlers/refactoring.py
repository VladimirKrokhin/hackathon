import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.enums.parse_mode import ParseMode

from app import dp
from bot.states import ContentGeneration
from bot.keyboards.inline import get_post_generation_keyboard
from services.content_generation import TextContentGenerationService

refactoring_router = Router(name="generation")


logger = logging.getLogger(__name__)


@refactoring_router.message(ContentGeneration.waiting_for_refactoring_text, F.text)
async def refactoring_text_handler(message: Message, state: FSMContext):
    refactoring_text = message.text.strip()
    await state.update_data(refactoring_text=refactoring_text)
    data = await state.get_data()
    content = await state.get_value("generated_post")

    generated_post = None

    await message.answer("🧠 Преобразую контент с помощью YandexGPT...", reply_markup=ReplyKeyboardRemove())

    try:
        text_content_generation_service: TextContentGenerationService = dp["text_content_generation_service"]
        generated_post = await text_content_generation_service.refactor_text_content(data,
                                                                                      content,
                                                                                      refactoring_text)
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

    await message.answer(
        "✨ Все материалы готовы к публикации! Что хотите сделать дальше?",
        reply_markup=get_post_generation_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_confirmation)
