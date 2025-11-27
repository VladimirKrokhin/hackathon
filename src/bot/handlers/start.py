import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext

from models import Ngo

from services.ngo_service import NGOService

from bot import dispatcher

from bot.handlers.ngo_info import VIEW_NGO_INFO_CALLBACK_DATA
from bot.handlers.content_plan_menu import CONTENT_PLAN_MENU_CALLBACK_DATA
from bot.handlers.image_generation import GENERATE_IMAGES_CALLBACK_DATA
from bot.handlers.text_editing import EDIT_TEXT_CALLBACK_DATA
from bot.handlers.wizard_handler import WIZARD_CREATE_CONTENT


logger = logging.getLogger(__name__)

start_router = Router(name="start")

BACK_TO_START_MENU_CALLBACK_DATA = "back_to_start_menu"
BACK_TO_MAIN_MENU_CALLBACK_DATA = "back_to_main"


@start_router.callback_query(F.data == BACK_TO_MAIN_MENU_CALLBACK_DATA)
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""

    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)




START_MENU_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создание контента", callback_data=WIZARD_CREATE_CONTENT)],
        [InlineKeyboardButton(text="📅 Управление контент-планами", callback_data=CONTENT_PLAN_MENU_CALLBACK_DATA)],
        # FIXME: "Редактировать текст" не работает
        # [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data=EDIT_TEXT_CALLBACK_DATA)],
        [InlineKeyboardButton(text="🎨 Генерация картинок", callback_data=GENERATE_IMAGES_CALLBACK_DATA)],
        [InlineKeyboardButton(text="📋 Информация о НКО", callback_data=VIEW_NGO_INFO_CALLBACK_DATA)],
    ]
)


BACK_TO_START_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Вернуться в главное меню", callback_data=BACK_TO_START_MENU_CALLBACK_DATA)],
    ]
)

# TODO: реализуй обработку возвращения в главное меню


@start_router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """Точка входа - главное меню с выбором режима работы."""
    await state.clear()

    # Проверяем наличие данных об НКО в БД
    ngo_service: NGOService = dispatcher["ngo_service"]
    user_id: int = message.from_user.id

    welcome_text = "👋 Привет! Я — Публикун, ваш AI-ассистент для создания контента в НКО.\n\n"

    if ngo_service.ngo_exists(user_id):
        # Если у пользователя есть данные НКО в БД, получаем их
        ngo_data: Ngo = ngo_service.get_ngo_data_by_user_id(user_id)
        ngo_name: str = ngo_data.name
        welcome_text += (
            f"🏢 У вас заполнена информация о НКО:\n"
            f"{ngo_name}\n\n"
            "Я могу создавать персонализированный контент с упоминанием вашей организации.\n\n"
        )

    else:
        welcome_text += "Я помогу вам подготовить профессиональные посты и карточки для соцсетей за пару минут.\n\n"

    welcome_text += (
        "📋 Доступные команды:\n"
        "• /start — текущее меню\n\n"
        "Что вы хотите сделать?"
    )

    from bot.handlers import ABOUT_PHOTO

    await message.answer_photo(
        photo=ABOUT_PHOTO,
        caption=welcome_text,
        reply_markup=START_MENU_KEYBOARD,
        )


@start_router.callback_query(F.data == BACK_TO_START_MENU_CALLBACK_DATA)
async def start_callback_query_handler(callback: CallbackQuery, state: FSMContext):
    await start_handler(callback.message, state)