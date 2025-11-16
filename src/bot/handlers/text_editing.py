import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.enums.parse_mode import ParseMode

from app import dp
from bot.states import EditText
from bot.keyboards.inline import get_skip_keyboard
from services.content_generation import TextContentGenerationService


text_editing_router = Router(name="text_editing")
logger = logging.getLogger(__name__)


@text_editing_router.message(Command("edittext"))
async def start_edit_text(message: Message, state: FSMContext):
    from bot.keyboards.inline import get_main_menu_keyboard

    await state.clear()
    await message.answer(
        "📝 **Редактирование текста через команду**\n\n"
        "Введите полностью текст, который нужно исправить.\n\n"
        "_Вы можете использовать эту команду или кнопки в меню._",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )

    await state.set_state(EditText.waiting_for_text)


@text_editing_router.message(EditText.waiting_for_text, F.text)
async def text_handler(message: Message, state: FSMContext):
    from bot.keyboards.inline import get_skip_keyboard, get_main_menu_keyboard

    text_to_edit = message.text.strip()
    if not text_to_edit:
        await message.answer(
            "⚠️ Пожалуйста, напишите текст, который хотите исправить.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    # Проверка на слишком короткий текст
    if len(text_to_edit.strip()) < 3:
        await message.answer(
            "⚠️ Текст слишком короткий для редактирования. Введите текст не менее 3 символов.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        return

    await state.update_data(text_to_edit=text_to_edit)

    # Проверяем наличие данных НКО для улучшения редактирования
    from app import dp
    ngo_service = dp["ngo_service"]
    user_id = message.from_user.id

    if ngo_service.ngo_exists(user_id):
        ngo_data = ngo_service.get_ngo_data(user_id)
        if ngo_data:
            await state.update_data(
                has_ngo_info=True,
                ngo_name=ngo_data.get("ngo_name", ""),
                ngo_description=ngo_data.get("ngo_description", ""),
                ngo_activities=ngo_data.get("ngo_activities", ""),
                ngo_contact=ngo_data.get("ngo_contact", ""),
            )

    await message.answer(
        "✒️ **Уточнение для редактирования**\n\n"
        "Хотите ли вы добавить дополнительные инструкции или пожелания по редактированию текста?\n\n"
        "_Например: «Сделать текст более формальным» или «Исправить только грамматику»_",
        reply_markup=get_skip_keyboard("⏭️ Пропустить уточнения"),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(EditText.waiting_for_details)


@text_editing_router.message(EditText.waiting_for_details, F.text)
async def details_handler(message: Message, state: FSMContext):
    from bot.keyboards.inline import get_main_menu_keyboard

    details = message.text.strip()
    if details == "⏭️ Пропустить уточнения":
        details = ""
    await state.update_data(details=details)

    data = await state.get_data()

    # Данные НКО уже должны быть в состоянии после выбора пользователя
    # Если их нет, но пользователь хотел использовать НКО, попробуем получить из БД
    if data.get("has_ngo_info") and not data.get("ngo_name"):
        ngo_service = dp["ngo_service"]
        user_id = message.from_user.id
        ngo_data = ngo_service.get_ngo_data(user_id)
        if ngo_data:
            data.update({
                "ngo_name": ngo_data.get("ngo_name", ""),
                "ngo_description": ngo_data.get("ngo_description", ""),
                "ngo_activities": ngo_data.get("ngo_activities", ""),
                "ngo_contact": ngo_data.get("ngo_contact", ""),
            })
            await state.update_data(**data)

    await message.answer(
        "✏️ **Редактирую текст...**\n\n_Это может занять 10-30 секунд._",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        text_generation_service: TextContentGenerationService = dp["text_content_generation_service"]
        generated_text = await text_generation_service.edit_text(data)
        await state.update_data(generated_text=generated_text)
    except Exception as error:
        logger.exception("Ошибка при редактировании текста: %s", error)
        await message.answer(
            "⚠️ **Не удалось отредактировать текст**\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.clear()
        return

    await message.answer(
        f"✅ **Результат редактирования:**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await message.answer(
        generated_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(),
    )

    await state.clear()
