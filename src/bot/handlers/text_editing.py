import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.enums.parse_mode import ParseMode

from app import dp
from bot.states import EditText
from bot.keyboards.reply import (
    get_skip_keyboard,
    SKIP_OPTION,
)
from services.content_generation import TextContentGenerationService


text_editing_router = Router(name="text_editing")
logger = logging.getLogger(__name__)


@text_editing_router.message(Command("edittext"))
async def start_edit_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📝 Давайте отредактируем ваш текст!\n\n"
        "Введите полностью текст, который нужно исправить."
    )

    await state.set_state(EditText.waiting_for_text)


@text_editing_router.message(EditText.waiting_for_text, F.text)
async def text_handler(message: Message, state: FSMContext):
    text_to_edit = message.text.strip()
    if not text_to_edit:
        await message.answer(
            "Пожалуйста, напишите текст, который хотите исправить."
        )
        return

    await state.update_data(text_to_edit=text_to_edit)

    await message.answer(
        "✒️ Хотели бы вы что-то уточнить при исправлении текста?",
        reply_markup=get_skip_keyboard(),
    )
    await state.set_state(EditText.waiting_for_details)


@text_editing_router.message(EditText.waiting_for_details, F.text)
async def details_handler(message: Message, state: FSMContext):
    details = message.text.strip()
    if details == SKIP_OPTION:
        details = ""
    await state.update_data(details=details)

    data = await state.get_data()

    await message.answer("🧠 Генерирую контент-план...")

    try:
        text_generation_service: TextContentGenerationService = dp["text_content_generation_service"]
        generated_text = await text_generation_service.edit_text(data)
        await state.update_data(generated_text=generated_text)
    except Exception as error:
        logger.exception("Ошибка при редактировании текста: %s", error)
        await message.answer(
            "⚠️ Не удалось получить ответ."
        )
        raise error

    await message.answer(
        f"✅ Ваш отредактированный текст:",
    )
    await message.answer(generated_text, parse_mode=ParseMode.MARKDOWN)

    await state.clear()
