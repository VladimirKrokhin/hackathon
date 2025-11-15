import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.states import ContentGeneration, NGOInfo
from bot.keyboards.reply import (
    get_generation_mode_keyboard, 
    get_ngo_main_keyboard,
    GENERATION_MODES
)
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
            await message.answer(
                f"👋 Привет! Я — ContentHelper, ваш AI-ассистент для создания контента в НКО.\n\n"
                f"🏢 У вас заполнена информация о НКО: {ngo_name}\n"
                f"Теперь я могу создавать персонализированный контент с упоминанием вашей организации.\n\n"
                f"Что вы хотите сделать?",
                reply_markup=get_ngo_main_keyboard(),
            )
        else:
            await message.answer(
                "👋 Привет! Я — ContentHelper, ваш AI-ассистент для создания контента в НКО.\n\n"
                "Я помогу вам подготовить профессиональные посты и карточки для соцсетей за пару минут.\n\n"
                "Вы можете заполнить информацию о вашей НКО для создания персонализированного контента, "
                "или сразу начать создавать контент без указания НКО.\n\n"
                "Что вы хотите сделать?",
                reply_markup=get_ngo_main_keyboard(),
            )
    else:
        await message.answer(
            "👋 Привет! Я — ContentHelper, ваш AI-ассистент для создания контента в НКО.\n\n"
            "Я помогу вам подготовить профессиональные посты и карточки для соцсетей за пару минут.\n\n"
            "Вы можете заполнить информацию о вашей НКО для создания персонализированного контента, "
            "или сразу начать создавать контент без указания НКО.\n\n"
            "Что вы хотите сделать?",
            reply_markup=get_ngo_main_keyboard(),
        )


@start_router.message(Command("ngo"))
async def ngo_command_handler(message: Message, state: FSMContext):
    """Обработчик команды /ngo - переход к сценарию сбора информации об НКО."""
    # Импортируем здесь, чтобы избежать циклических импортов
    from bot.handlers.ngo_info import ngo_command_handler as ngo_handler
    await ngo_handler(message, state)


@start_router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Команда для сброса текущего сценария."""
    await state.clear()
    await message.answer(
        "❎ Текущий сценарий сброшен.\n\n"
        "Что вы хотите сделать?",
        reply_markup=get_ngo_main_keyboard(),
    )


@start_router.message(F.text == "🏢 Заполнить информацию об НКО")
async def ngo_menu_handler(message: Message, state: FSMContext):
    """Обработчик кнопки главного меню для заполнения информации об НКО."""
    from bot.handlers.ngo_info import ngo_command_handler as ngo_handler
    await ngo_handler(message, state)


@start_router.message(F.text == "📝 Создать контент (структурированная форма)")
async def structured_content_handler(message: Message, state: FSMContext):
    """Обработчик для создания контента в структурированной форме."""
    await state.clear()
    await state.update_data(generation_mode="structured", has_ngo_info=False)
    
    await message.answer(
        "📝 Отлично! Переходим к структурированной форме.\n\n"
        "Для создания персонализированного контента с данными НКО - выберите 'Да'.\n"
        "Или продолжите без данных НКО - выберите 'Нет'.",
        reply_markup=get_yes_no_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_ngo_info_choice)


@start_router.message(F.text == "💭 Создать контент (свободная форма)")
async def free_form_content_handler(message: Message, state: FSMContext):
    """Обработчик для создания контента в свободной форме."""
    await state.clear()
    await state.update_data(generation_mode="free_form", has_ngo_info=False)
    
    await message.answer(
        "💭 Понятно! Используем свободную форму создания.\n\n"
        "Для создания персонализированного контента с данными НКО - выберите 'Да'.\n"
        "Или продолжите без данных НКО - выберите 'Нет'.",
        reply_markup=get_yes_no_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_ngo_info_choice)


@start_router.message(F.text == "✏️ Редактировать контент")
async def edit_text_handler(message: Message, state: FSMContext):
    """Обработчик для создания контента в свободной форме."""
    await state.clear()
    await state.update_data(edit_text=True, has_ngo_info=False)

    await message.answer(
        "✏️ Хорошо! Редактируем исходный текст.\n\n"
        "Для создания персонализированного контента с данными НКО - выберите 'Да'.\n"
        "Или продолжите без данных НКО - выберите 'Нет'.",
        reply_markup=get_yes_no_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_ngo_info_choice)


@start_router.message(F.text == "📋 Посмотреть мою НКО")
async def view_ngo_handler(message: Message, state: FSMContext):
    """Обработчик для просмотра информации об НКО."""
    from bot.handlers.ngo_info import view_ngo_info_handler as view_handler
    await view_handler(message, state)


@start_router.message(F.text == "🔄 Обновить данные НКО")
async def update_ngo_handler(message: Message, state: FSMContext):
    """Обработчик для обновления данных НКО."""
    from bot.handlers.ngo_info import update_ngo_info_handler as update_handler
    await update_handler(message, state)


# Дополнительные импорты для кнопок yes/no
from bot.keyboards.reply import get_yes_no_keyboard
