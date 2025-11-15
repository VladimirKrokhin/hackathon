import logging

from aiogram import Router, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message, ReplyKeyboardRemove

from bot.handlers.start import start_handler
from bot.states import ContentGeneration

callbacks_router = Router(name="callbacks")
logger = logging.getLogger(__name__)


# === ГЛАВНОЕ МЕНЮ ===
@callbacks_router.callback_query(F.data == "create_content")
async def create_content_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик создания контента - показывает меню создания контента."""
    await callback.answer()
    from bot.keyboards.inline import get_content_creation_menu_keyboard
    
    await callback.message.edit_text(
        "📝 Создание контента\n\n"
        "Выберите действие:",
        reply_markup=get_content_creation_menu_keyboard()
    )


@callbacks_router.callback_query(F.data == "ngo_info")
async def ngo_info_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик информации о НКО - проверяет наличие данных и показывает меню."""
    await callback.answer()
    from app import dp
    from bot.keyboards.inline import get_ngo_info_menu_keyboard
    
    ngo_service = dp["ngo_service"]
    user_id = callback.from_user.id
    
    # Проверяем наличие данных НКО
    has_ngo_data = ngo_service.ngo_exists(user_id)
    
    menu_text = "📋 Информация о НКО\n\n"
    if has_ngo_data:
        ngo_data = ngo_service.get_ngo_data(user_id)
        if ngo_data:
            ngo_name = ngo_data.get("ngo_name", "")
            menu_text += f"🏢 Ваша НКО: {ngo_name}\n\n"
    
    menu_text += "Выберите действие:"
    
    await callback.message.edit_text(
        menu_text,
        reply_markup=get_ngo_info_menu_keyboard(has_ngo_data),
        parse_mode=ParseMode.MARKDOWN,
    )


@callbacks_router.callback_query(F.data == "create_content_form")
async def create_content_form_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора формы создания контента."""
    await callback.answer()
    from bot.keyboards.inline import get_content_form_menu_keyboard
    
    await callback.message.edit_text(
        "📝 Создание контента\n\n"
        "Выберите форму создания:",
        reply_markup=get_content_form_menu_keyboard()
    )


@callbacks_router.callback_query(F.data == "back_to_content_menu")
async def back_to_content_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню создания контента."""
    await callback.answer()
    from bot.keyboards.inline import get_content_creation_menu_keyboard
    
    await callback.message.edit_text(
        "📝 Создание контента\n\n"
        "Выберите действие:",
        reply_markup=get_content_creation_menu_keyboard()
    )


@callbacks_router.callback_query(F.data == "yes_fill_ngo")
async def yes_fill_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик согласия заполнить данные НКО."""
    await callback.answer()
    await fill_ngo_handler(callback, state)


@callbacks_router.callback_query(F.data == "no_fill_ngo")
async def no_fill_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отказа заполнить данные НКО."""
    await callback.answer()
    from bot.keyboards.inline import get_goal_keyboard
    
    await state.clear()
    await state.update_data(has_ngo_info=False)
    
    await callback.message.edit_text(
        "✨ Понятно! Создаем контент без упоминания НКО.\n\n"
        "Какова основная цель вашего поста?",
        reply_markup=get_goal_keyboard()
    )
    await state.set_state(ContentGeneration.waiting_for_goal)


@callbacks_router.callback_query(F.data == "structured_content")
async def structured_content_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик структурированной формы."""
    await callback.answer()
    await state.clear()
    await state.update_data(generation_mode="structured", has_ngo_info=False)
    
    # Проверяем наличие данных НКО
    from app import dp
    ngo_service = dp["ngo_service"]
    user_id = callback.from_user.id
    
    if not ngo_service.ngo_exists(user_id):
        # Если данных НКО нет, предлагаем заполнить
        from bot.keyboards.inline import get_ngo_data_missing_keyboard
        
        await callback.message.edit_text(
            "📋 Структурированная форма\n\n"
            "У вас нет сохраненной информации об НКО. Хотите заполнить ее сейчас?",
            reply_markup=get_ngo_data_missing_keyboard()
        )
    else:
        # Если данные НКО есть, спрашиваем использовать ли их
        from bot.keyboards.inline import get_yes_no_keyboard
        
        await callback.message.edit_text(
            "📋 Структурированная форма\n\n"
            "Для создания персонализированного контента с данными НКО - выберите 'Да'.\n"
            "Или продолжите без данных НКО - выберите 'Нет'.",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(ContentGeneration.waiting_for_ngo_info_choice)


@callbacks_router.callback_query(F.data == "free_form_content")
async def free_form_content_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик свободной формы."""
    await callback.answer()
    await state.clear()
    await state.update_data(generation_mode="free_form", has_ngo_info=False)
    
    # Проверяем наличие данных НКО
    from app import dp
    ngo_service = dp["ngo_service"]
    user_id = callback.from_user.id
    
    if not ngo_service.ngo_exists(user_id):
        # Если данных НКО нет, предлагаем заполнить
        from bot.keyboards.inline import get_ngo_data_missing_keyboard
        
        await callback.message.edit_text(
            "💭 Свободная форма\n\n"
            "У вас нет сохраненной информации об НКО. Хотите заполнить ее сейчас?",
            reply_markup=get_ngo_data_missing_keyboard()
        )
    else:
        # Если данные НКО есть, спрашиваем использовать ли их
        from bot.keyboards.inline import get_yes_no_keyboard
        
        await callback.message.edit_text(
            "💭 Свободная форма\n\n"
            "Для создания персонализированного контента с данными НКО - выберите 'Да'.\n"
            "Или продолжите без данных НКО - выберите 'Нет'.",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(ContentGeneration.waiting_for_ngo_info_choice)


@callbacks_router.callback_query(F.data == "view_ngo")
async def view_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик просмотра НКО."""
    await callback.answer()
    from app import dp
    
    ngo_service = dp["ngo_service"]
    user_id = callback.from_user.id
    
    summary = ngo_service.get_ngo_summary(user_id)
    
    if not summary:
        await callback.message.edit_text(
            "❌ У вас пока нет сохраненной информации об НКО.\n\n"
            "Хотите заполнить ее сейчас?",
            reply_markup=get_ngo_data_missing_keyboard()
        )
        return
    
    from bot.keyboards.inline import get_ngo_info_menu_keyboard
    
    await callback.message.edit_text(
        summary + "\n\nВыберите действие:",
        reply_markup=get_ngo_info_menu_keyboard(True),
        parse_mode=ParseMode.MARKDOWN,
    )


@callbacks_router.callback_query(F.data == "update_ngo")
async def update_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик обновления НКО."""
    await callback.answer()
    from bot.keyboards.inline import get_ngo_navigation_keyboard
    from bot.states import NGOInfo
    
    await state.clear()
    await state.set_state(NGOInfo.waiting_for_ngo_name)
    
    await callback.message.edit_text(
        "🔄 Обновление данных НКО\n\n"
        "Введите новое название НКО (или текущее, если не хотите менять):",
        reply_markup=get_ngo_navigation_keyboard()
    )


@callbacks_router.callback_query(F.data == "fill_ngo")
async def fill_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик заполнения НКО."""
    await callback.answer()
    from bot.keyboards.inline import get_ngo_navigation_keyboard
    
    await callback.message.edit_text(
        "🏢 Отлично! Давайте заполним информацию о вашей НКО.\n\n"
        "Это поможет мне создавать персонализированный контент с упоминанием вашей организации.\n\n"
        "Укажите наименование НКО:",
        reply_markup=get_ngo_navigation_keyboard()
    )
    from bot.states import NGOInfo
    await state.set_state(NGOInfo.waiting_for_ngo_name)


@callbacks_router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


@callbacks_router.callback_query(F.data == "yes")
async def yes_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответа 'Да'."""
    await callback.answer()
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "")
    
    if generation_mode in ["structured", "free_form"]:
        await state.update_data(has_ngo_info=True)
        # Переход к обработчику НКО
        from bot.handlers.ngo_info import ngo_command_handler as ngo_handler
        await ngo_handler(callback.message, state)


@callbacks_router.callback_query(F.data == "no")
async def no_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответа 'Нет'."""
    await callback.answer()
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "")
    
    if generation_mode == "structured":
        # Переход к структурированной форме без НКО
        await structured_generation_handler(callback.message, state)
    elif generation_mode == "free_form":
        # Переход к свободной форме без НКО
        await free_form_generation_handler(callback.message, state)


# === СУЩЕСТВУЮЩИЕ ОБРАБОТЧИКИ ===
@callbacks_router.callback_query(F.data == "create_again")
async def create_again_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


@callbacks_router.callback_query(F.data == "get_tips")
async def get_tips_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    platform = data.get("platform", "")
    audience = ", ".join(data.get("audience", [])) or "не указана"
    goal = data.get("goal", "вашей задачи")

    tips_text = (
        "💡 Общие советы по продвижению:\n\n"
        "• Публикуйте регулярно, чтобы аудитория не забывала о вас\n"
        "• Комбинируйте информационный и эмоциональный контент\n"
        "• Задавайте вопросы в постах для повышения вовлечённости\n"
        "• Анализируйте статистику и корректируйте стратегию\n"
        "• Сотрудничайте с другими НКО для взаимного продвижения"
    )

    await callback.message.answer(
        f"Цель: {goal}\nАудитория: {audience}\nПлатформа: {platform or '—'}\n\n{tips_text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Создать ещё", callback_data="create_again")],
            ]
        ),
    )


@callbacks_router.callback_query(F.data == "refactor_content")
async def refactor_content_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "✍️ Давайте отредактируем созданный текст!\n"
        "Напишите, что бы вы хотели изменить:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentGeneration.waiting_for_refactoring_text)


# === НАВИГАЦИЯ ===
@callbacks_router.callback_query(F.data == "back_to_previous")
async def back_to_previous_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к предыдущему шагу."""
    await callback.answer()
    await state.clear()
    from bot.handlers.start import start_handler
    await start_handler(callback.message, state)


@callbacks_router.callback_query(F.data == "skip_step")
async def skip_step_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска шага."""
    await callback.answer()
    await callback.message.answer(
        "Шаг пропущен.",
        reply_markup=ReplyKeyboardRemove(),
    )


@callbacks_router.callback_query(F.data == "done")
async def done_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик завершения процесса."""
    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


# === ЛОКАЛЬНЫЕ ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ КОНТЕНТА ===

async def structured_generation_handler(message: Message, state: FSMContext):
    """Прямой запуск структурированной формы генерации контента."""
    await message.answer(
        "📝 Отлично! Начинаем структурированную форму.\n\n"
        "**Что за событие?**\n"
        "Опишите коротко, о каком событии будет пост.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN
    )
    await state.set_state(ContentGeneration.waiting_for_event_type)


async def free_form_generation_handler(message: Message, state: FSMContext):
    """Прямой запуск свободной формы генерации контента."""
    await message.answer(
        "💭 Понятно! Используем свободную форму.\n\n"
        "**Опишите ваш пост**\n"
        "Расскажите подробно, о чём будет пост, какую информацию нужно донести.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_user_description)


# Функция для получения клавиатуры при отсутствии данных НКО
def get_ngo_data_missing_keyboard():
    """Получить клавиатуру при отсутствии данных НКО."""
    from bot.keyboards.inline import get_ngo_data_missing_keyboard as func
    return func()


# Функция для получения клавиатуры целей
def get_goal_keyboard():
    """Получить клавиатуру выбора цели."""
    from bot.keyboards.inline import get_goal_keyboard as func
    return func()
