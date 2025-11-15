import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.states import ContentGeneration, NGOInfo
from bot.keyboards.inline import get_main_menu_keyboard
from app import dp

logger = logging.getLogger(__name__)

start_router = Router(name="start")


@start_router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """Точка входа - главное меню с выбором режима работы."""
    await state.clear()
    
    # Проверяем наличие данных об НКО в БД
    ngo_service = dp["ngo_service"]
    user_id = message.from_user.id
    
    if ngo_service.ngo_exists(user_id):
        # Если у пользователя есть данные НКО в БД, получаем их
        ngo_data = ngo_service.get_ngo_data(user_id)
        if ngo_data:
            ngo_name = ngo_data.get("ngo_name", "")
            welcome_text = (
                f"👋 Привет! Я — Публикун, ваш AI-ассистент для создания контента в НКО.\n\n"
                f"🏢 У вас заполнена информация о НКО: {ngo_name}\n"
                f"Теперь я могу создавать персонализированный контент с упоминанием вашей организации.\n\n"
                f"📋 Доступные команды:\n"
                f"• /start — текущее меню\n"
                f"• /menu — меню действий\n"
                f"• /ngo — работа с данными НКО\n"
                f"• /cancel — отменить текущее действие\n\n"
                f"Что вы хотите сделать?"
            )
        else:
            welcome_text = (
                "👋 Привет! Я — Публикун, ваш AI-ассистент для создания контента в НКО.\n\n"
                "Я помогу вам подготовить профессиональные посты и карточки для соцсетей за пару минут.\n\n"
                "📋 Доступные команды:\n"
                "• /start — текущее меню\n"
                "• /menu — меню действий\n"
                "• /ngo — работа с данными НКО\n"
                "• /cancel — отменить текущее действие\n\n"
                "Что вы хотите сделать?"
            )
    else:
        welcome_text = (
            "👋 Привет! Я — Публикун, ваш AI-ассистент для создания контента в НКО.\n\n"
            "Я помогу вам подготовить профессиональные посты и карточки для соцсетей за пару минут.\n\n"
            "📋 Доступные команды:\n"
            "• /start — текущее меню\n"
            "• /menu — меню действий\n"
            "• /ngo — работа с данными НКО\n"
            "• /cancel — отменить текущее действие\n\n"
            "Что вы хотите сделать?"
        )

    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
    )


@start_router.message(Command("ngo"))
async def ngo_command_handler(message: Message, state: FSMContext):
    """Обработчик команды /ngo - переход к сценарию сбора информации об НКО."""
    # Импортируем здесь, чтобы избежать циклических импортов
    from bot.handlers.ngo_info import ngo_command_handler as ngo_handler
    await ngo_handler(message, state)


@start_router.message(Command("menu"))
async def main_menu_handler(message: Message, state: FSMContext):
    """Обработчик команды /menu - показ главного меню с inline кнопками."""
    # Проверяем наличие данных об НКО в БД
    ngo_service = dp["ngo_service"]
    user_id = message.from_user.id
    
    menu_text = "👋 Главное меню\n\nЧто вы хотите сделать?"
    
    # Проверяем, есть ли у пользователя данные НКО
    if ngo_service.ngo_exists(user_id):
        ngo_data = ngo_service.get_ngo_data(user_id)
        if ngo_data:
            ngo_name = ngo_data.get("ngo_name", "")
            menu_text = f"👋 Главное меню\n\n🏢 Ваша НКО: {ngo_name}\n\nЧто вы хотите сделать?"
    
    await message.answer(
        menu_text,
        reply_markup=get_main_menu_keyboard(),
    )


@start_router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Команда для сброса текущего сценария."""
    await state.clear()
    await message.answer(
        "❎ Текущий сценарий сброшен.\n\nЧто вы хотите сделать?",
        reply_markup=get_main_menu_keyboard(),
    )
