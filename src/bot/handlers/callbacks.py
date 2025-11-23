import logging

from aiogram import Router, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message, ReplyKeyboardRemove

from bot.handlers.start import start_handler
from bot.states import ContentGeneration, ContentPlan
from app import dp

callbacks_router = Router(name="callbacks")
logger = logging.getLogger(__name__)


# === ГЛАВНОЕ МЕНЮ ===
@callbacks_router.callback_query(F.data == "create_content")
async def create_content_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик создания контента - напрямую показывает меню форм создания."""
    await callback.answer()
    from bot.keyboards.inline import get_content_form_menu_keyboard

    await callback.message.answer(
        "📝 Создание контента\n\n"
        "Выберите форму создания:",
        reply_markup=get_content_form_menu_keyboard()
    )


@callbacks_router.callback_query(F.data == "generate_images")
async def generate_images_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик генерации изображений."""
    await callback.answer()
    await state.clear()

    await callback.message.answer(
        "🎨 Генерация изображений\n\n"
        "Я могу помочь вам сгенерировать картинки для ваших постов!\n\n"
        "**Какое изображение вы хотите сгенерировать?**\n\n"
        "Опишите тему и стиль изображения, например:\n"
        "• Портрет волонтера в солнечном парке\n"
        "• Группа детей за благотворительным мероприятием\n"
        "• Иконка для сбора средств на помощь животным\n"
        "• Иллюстрация для поста о защите окружающей среды\n\n"
        "Или нажмите кнопку ниже для генерации на основе уже созданного контента.",
        reply_markup=get_image_generation_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
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
    
    await callback.message.answer(
        menu_text,
        reply_markup=get_ngo_info_menu_keyboard(has_ngo_data),
        parse_mode=ParseMode.MARKDOWN,
    )


@callbacks_router.callback_query(F.data == "create_content_form")
async def create_content_form_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора формы создания контента."""
    await callback.answer()
    from bot.keyboards.inline import get_content_form_menu_keyboard
    
    await callback.message.answer(
        "📝 Создание контента\n\n"
        "Выберите форму создания:",
        reply_markup=get_content_form_menu_keyboard()
    )


@callbacks_router.callback_query(F.data == "back_to_content_menu")
async def back_to_content_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню создания контента."""
    await callback.answer()
    from bot.keyboards.inline import get_content_creation_menu_keyboard
    
    await callback.message.answer(
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
    # await callback.answer()
    # from bot.keyboards.inline import get_goal_keyboard
    #
    # await state.clear()
    # await state.update_data(has_ngo_info=False)
    #
    # await callback.message.answer(
    #     "✨ Понятно! Создаем контент без упоминания НКО.\n\n"
    #     "Какова основная цель вашего поста?",
    #     reply_markup=get_goal_keyboard()
    # )
    # await state.set_state(ContentGeneration.waiting_for_goal)

    await callback.answer()
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "")
    await callback.message.answer(
        "✨ Понятно! Создаем контент без упоминания НКО.\n\n"
    )
    if generation_mode == "structured":
        # Переход к структурированной форме без НКО
        await structured_generation_handler(callback.message, state)
    elif generation_mode == "free_form":
        # Переход к свободной форме без НКО
        await free_form_generation_handler(callback.message, state)


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
        
        await callback.message.answer(
            "📋 Структурированная форма\n\n"
            "У вас нет сохраненной информации об НКО. Хотите заполнить ее сейчас?",
            reply_markup=get_ngo_data_missing_keyboard()
        )
    else:
        # Если данные НКО есть, спрашиваем использовать ли их
        from bot.keyboards.inline import get_yes_no_keyboard
        
        await callback.message.answer(
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
        
        await callback.message.answer(
            "💭 Свободная форма\n\n"
            "У вас нет сохраненной информации об НКО. Хотите заполнить ее сейчас?",
            reply_markup=get_ngo_data_missing_keyboard()
        )
    else:
        # Если данные НКО есть, спрашиваем использовать ли их
        from bot.keyboards.inline import get_yes_no_keyboard
        
        await callback.message.answer(
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
        await callback.message.answer(
            "❌ У вас пока нет сохраненной информации об НКО.\n\n"
            "Хотите заполнить ее сейчас?",
            reply_markup=get_ngo_data_missing_keyboard()
        )
        return
    
    from bot.keyboards.inline import get_ngo_info_menu_keyboard
    
    await callback.message.answer(
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
    
    await callback.message.answer(
        "🔄 Обновление данных НКО\n\n"
        "Введите новое название НКО (или текущее, если не хотите менять):",
        reply_markup=get_ngo_navigation_keyboard()
    )


@callbacks_router.callback_query(F.data == "fill_ngo")
async def fill_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик заполнения НКО."""
    await callback.answer()
    from bot.keyboards.inline import get_ngo_navigation_keyboard
    
    await callback.message.answer(
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
    current_state = await state.get_state()

    if generation_mode in ["structured", "free_form"]:
        # Если мы в состоянии выбора НКО для генерации контента
        if current_state == ContentGeneration.waiting_for_ngo_info_choice:
            await state.update_data(has_ngo_info=True)
            # Загружаем данные НКО из БД и переходим к генерации контента
            from app import dp
            ngo_service = dp["ngo_service"]
            user_id = callback.from_user.id
            ngo_data = ngo_service.get_ngo_data(user_id)

            if ngo_data:
                await state.update_data(**ngo_data)

            if generation_mode == "structured":
                await structured_generation_handler(callback.message, state)
            else:  # free_form
                await free_form_generation_handler(callback.message, state)

            return

        # Для других случаев - переход к обработчику НКО
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


@callbacks_router.callback_query(F.data == "content_plan")
async def content_plan_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик контент-плана - запускает функцию составления контент-плана."""
    await callback.answer()
    from bot.keyboards.inline import get_period_keyboard

    await state.clear()
    await callback.message.answer(
        "📅 Давайте создадим контент-план для ваших постов!\n\n"
        "На какой период вы хотите подготовить план?",
        reply_markup=get_period_keyboard(),
    )
    from bot.states import ContentPlan
    await state.set_state(ContentPlan.waiting_for_period)


@callbacks_router.callback_query(F.data == "edit_text")
async def edit_text_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик редактирования текста - запускает процесс редактирования."""
    await callback.answer()
    await state.clear()

    await callback.message.answer(
        "📝 Редактирование текста\n\n"
        "Эта функция поможет исправить грамматику, орфографию, стиль и логику вашего текста.\n\n"
        "**Что сделать?**",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Начать редактирование", callback_data="start_text_editing")],
                [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main")]
            ]
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


@callbacks_router.callback_query(F.data == "start_text_editing")
async def start_text_editing_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала редактирования текста."""
    await callback.answer()
    from bot.states import EditText

    await state.clear()
    await state.set_state(EditText.waiting_for_text)

    await callback.message.edit_text(
        "📝 **Редактирование текста**\n\n"
        "Введите полностью текст, который нужно исправить.\n\n"
        "_Вы можете отправить любой текст для исправления грамматики, орфографии, стиля и логики._",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main")]
            ]
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


@callbacks_router.callback_query(F.data == "refactor_content")
async def refactor_content_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "✍️ Давайте отредактируем созданный текст!\n"
        "Напишите, что бы вы хотели изменить:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentGeneration.waiting_for_refactoring_text)


# === ОБРАБОТЧИКИ ВЫБОРА СТИЛЯ ПОВЕСТВОВАНИЯ ===
@callbacks_router.callback_query(F.data == "narrative_conversational")
async def narrative_conversational_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора разговорного стиля."""
    await callback.answer()
    await narrative_style_handler_common(callback, state, "💬 Разговорный стиль")


@callbacks_router.callback_query(F.data == "narrative_official")
async def narrative_official_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора официально-делового стиля."""
    await callback.answer()
    await narrative_style_handler_common(callback, state, "📋 Официально-деловой стиль")


@callbacks_router.callback_query(F.data == "narrative_artistic")
async def narrative_artistic_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора художественного стиля."""
    await callback.answer()
    await narrative_style_handler_common(callback, state, "🎨 Художественный стиль")


@callbacks_router.callback_query(F.data == "narrative_motivational")
async def narrative_motivational_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора позитивного/мотивирующего стиля."""
    await callback.answer()
    await narrative_style_handler_common(callback, state, "🌟 Позитивный/мотивирующий стиль")


async def narrative_style_handler_common(callback: CallbackQuery, state: FSMContext, style_name: str):
    """Общий обработчик для всех стилей повествования."""
    await state.update_data(narrative_style=style_name)
    
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "")
    
    if generation_mode == "free_form":
        # Для свободной формы - сразу переходим к выбору платформы
        await callback.message.answer(
            "📱 **На какой платформе будет публиковаться пост?**",
            reply_markup=get_platform_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_platform)
    else:
        # Для структурированной формы - сразу переходим к выбору платформы
        await callback.message.answer(
            "📱 **На какой платформе будет публиковаться пост?**",
            reply_markup=get_platform_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_platform)


# === ОБРАБОТЧИКИ ВЫБОРА ПЛАТФОРМЫ ===
@callbacks_router.callback_query(F.data == "platform_vk")
async def platform_vk_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора ВКонтакте."""
    await callback.answer()
    await platform_handler_common(callback, state, "📱 ВКонтакте (для молодежи)")


@callbacks_router.callback_query(F.data == "platform_telegram")
async def platform_telegram_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора Telegram."""
    await callback.answer()
    await platform_handler_common(callback, state, "💬 Telegram (для взрослых/бизнеса)")


@callbacks_router.callback_query(F.data == "platform_instagram")
async def platform_instagram_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора Instagram."""
    await callback.answer()
    await platform_handler_common(callback, state, "📸 Instagram (визуальный контент)")


async def platform_handler_common(callback: CallbackQuery, state: FSMContext, platform_name: str):
    """Общий обработчик для всех платформ - переход к выбору источника изображения."""
    await state.update_data(platform=platform_name)

    # Новый шаг: выбор источника изображения перед генерацией карточек
    await callback.message.answer(
        "🖼️ **Выберите источник тематической картинки для карточки:**",
        reply_markup=get_image_source_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_image_source)


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


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def get_ngo_data_missing_keyboard():
    """Получить клавиатуру при отсутствии данных НКО."""
    from bot.keyboards.inline import get_ngo_data_missing_keyboard as func
    return func()


# Функция для получения клавиатуры целей
def get_goal_keyboard():
    """Получить клавиатуру выбора цели."""
    from bot.keyboards.inline import get_goal_keyboard as func
    return func()


def get_platform_keyboard():
    """Получить клавиатуру выбора платформы."""
    from bot.keyboards.inline import get_platform_keyboard as func
    return func()


# === ОБРАБОТЧИКИ ДЛЯ НКО ПРОЦЕССА ===
@callbacks_router.callback_query(F.data == "ngo_cancel")
async def ngo_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены процесса НКО."""
    await callback.answer()
    await state.clear()
    from bot.keyboards.inline import get_ngo_main_keyboard

    await callback.message.answer(
        "❎ Процесс сбора информации об НКО отменен.",
        reply_markup=get_ngo_main_keyboard(),
    )


@callbacks_router.callback_query(F.data == "ngo_skip")
async def ngo_skip_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска шага в процессе НКО."""
    await callback.answer()

    current_state = await state.get_state()
    from bot.states import NGOInfo

    if current_state == NGOInfo.waiting_for_ngo_description:
        await state.update_data(ngo_description="Не указано")
        await callback.message.answer(
            f"✅ Описание: Не указано\n\n"
            "🎯 Какие формы деятельности ведет ваша НКО? (например: благотворительность, просвещение, помощь животным и т.д.)\n\n"
            "Можете перечислить через запятую или нажать ⏩ Пропустить.",
            reply_markup=get_ngo_navigation_keyboard(),
        )
        await state.set_state(NGOInfo.waiting_for_ngo_activities)

    elif current_state == NGOInfo.waiting_for_ngo_activities:
        await state.update_data(ngo_activities="Не указано")
        await callback.message.answer(
            f"✅ Формы деятельности: Не указано\n\n"
            "📞 Укажите контактную информацию для связи (телефон, email, сайт или социальные сети)\n\n"
            "Можете указать любые удобные способы связи или нажать ⏩ Пропустить.",
            reply_markup=get_ngo_navigation_keyboard(),
        )
        await state.set_state(NGOInfo.waiting_for_ngo_contact)

    elif current_state == NGOInfo.waiting_for_ngo_contact:
        await state.update_data(ngo_contact="Не указано")
        # Показываем итоговую информацию для подтверждения
        data = await state.get_data()
        name = data.get("ngo_name", "")
        description = data.get("ngo_description", "Не указано")
        activities = data.get("ngo_activities", "Не указано")
        contact_info = "Не указано"

        summary = (
            f"🏢 **Информация о НКО \"{name}\"**\n\n"
            f"📝 **Описание:** {description}\n\n"
            f"🎯 **Деятельность:** {activities}\n\n"
            f"📞 **Контакты:** {contact_info}\n\n"
            "Подтверждаете данные? Их можно будет изменить позже."
        )

        await callback.message.answer(
            summary,
            reply_markup=get_ngo_navigation_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(NGOInfo.waiting_for_ngo_confirmation)


@callbacks_router.callback_query(F.data == "ngo_done")
async def ngo_done_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик завершения и подтверждения данных НКО."""
    await callback.answer()

    current_state = await state.get_state()
    from bot.states import NGOInfo
    from bot.keyboards.inline import get_main_menu_keyboard, get_ngo_navigation_keyboard

    if current_state == NGOInfo.waiting_for_ngo_confirmation:
        # Подтверждение данных НКО
        data = await state.get_data()
        ngo_name = data.get("ngo_name", "")

        # Получаем сервис НКО и сохраняем данные в БД
        from app import dp
        ngo_service = dp["ngo_service"]
        user_id = callback.from_user.id

        ngo_data = {
            "ngo_name": ngo_name,
            "description": data.get("ngo_description", "Не указано"),
            "activities": data.get("ngo_activities", "Не указано"),
            "contact": data.get("ngo_contact", "Не указано"),
        }

        # Валидируем данные
        is_valid, validation_message = ngo_service.validate_ngo_data(ngo_data)
        if not is_valid:
            await callback.message.answer(
                f"❌ Ошибка валидации: {validation_message}\n\n"
                "Попробуйте снова.",
                reply_markup=get_ngo_navigation_keyboard(),
            )
            return

        # Сохраняем в БД
        success = ngo_service.create_or_update_ngo(user_id, ngo_data)

        if success:
            await callback.message.answer(
                f"✅ Информация о НКО \"{ngo_name}\" успешно сохранена в базу данных!\n\n"
                "Теперь вы можете создавать персонализированный контент.\n\n"
                "💡 Выберите следующее действие или вернитесь в главное меню:",
                reply_markup=get_main_menu_keyboard(),
            )
            await state.clear()
        else:
            await callback.message.answer(
                "❌ Не удалось сохранить данные. Попробуйте позже.",
                reply_markup=get_ngo_navigation_keyboard(),
            )

    else:
        # Просто завершение текущего процесса
        await state.clear()
        from bot.handlers.start import start_handler
        await start_handler(callback.message, state)


def get_ngo_navigation_keyboard():
    """Получить клавиатуру навигации НКО."""
    from bot.keyboards.inline import get_ngo_navigation_keyboard as func
    return func()


# === ОБРАБОТЧИКИ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ ===
@callbacks_router.callback_query(F.data == "back_to_image_menu")
async def back_to_image_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню генерации изображений."""
    await callback.answer()
    await state.clear()

    await callback.message.answer(
        "🎨 Генерация изображений\n\n"
        "Выберите вариант генерации:",
        reply_markup=get_image_generation_keyboard(),
    )


@callbacks_router.callback_query(F.data == "back_to_style_selection")
async def back_to_style_selection_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору стиля изображения."""
    await callback.answer()

    await callback.message.answer(
        "🎭 **Выберите стиль генерации:**",
        reply_markup=get_image_style_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_image_style)


@callbacks_router.callback_query(F.data == "describe_image")
async def describe_image_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик описания изображения."""
    await callback.answer()
    await state.clear()
    await state.set_state(ContentGeneration.waiting_for_image_description)

    await callback.message.answer(
        "🎨 **Опишите изображение**\n\n"
        "Расскажите, какое изображение вы хотите получить. Будьте максимально подробны:\n\n"
        "• Какие объекты/люди должны быть на изображении?\n"
        "• Какое настроение/атмосфера?\n"
        "• Цветовая гамма? (яркая, пастельная, монохромная...)\n"
        "• Стиль изображения? (реалистичный, иллюстрация, минимализм...)\n\n"
        "_Пример: «Группа улыбающихся детей играет в парке на ярком солнце, теплые цвета, реалистичный стиль»_",
        parse_mode=ParseMode.MARKDOWN,
    )


@callbacks_router.callback_query(F.data == "image_from_content")
async def image_from_content_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик генерации изображения на основе созданного контента."""
    await callback.answer()

    # Проверяем наличие сгенерированного контента в состоянии
    data = await state.get_data()
    generated_content = data.get("generated_content", "")

    if not generated_content:
        await callback.message.answer(
            "❌ **У вас нет текущего сгенерированного контента**\n\n"
            "Сначала создайте пост, а потом сможете сгенерировать изображение на его основе.",
            reply_markup=get_image_generation_keyboard(),
        )
        return

    await state.update_data(generation_mode="image_from_content")
    await state.set_state(ContentGeneration.waiting_for_image_style)

    # Показываем превью контента и запрашиваем стиль
    preview = generated_content[:300] + "..." if len(generated_content) > 300 else generated_content

    await callback.message.answer(
        "🎭 **Генерация изображения на основе вашего контента**\n\n"
        "Превью контента:\n"
        f"```\n{preview}\n```\n\n"
        "**Выберите стиль генерации:**",
        reply_markup=get_image_style_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


# === ОБРАБОТЧИКИ ВЫБОРА СТИЛЯ ИЗОБРАЖЕНИЯ ===
@callbacks_router.callback_query(F.data == "image_style_realistic")
async def image_style_realistic_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора реалистичного стиля."""
    await callback.answer()
    await process_image_generation(callback, state, "реалистичный стиль")


@callbacks_router.callback_query(F.data == "image_style_illustration")
async def image_style_illustration_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора иллюстративного стиля."""
    await callback.answer()
    await process_image_generation(callback, state, "иллюстрация в ярком стиле")


@callbacks_router.callback_query(F.data == "image_style_minimal")
async def image_style_minimal_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора минималистичного стиля."""
    await callback.answer()
    await process_image_generation(callback, state, "минималистичный стиль")


@callbacks_router.callback_query(F.data == "image_style_abstract")
async def image_style_abstract_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора абстрактного стиля."""
    await callback.answer()
    await process_image_generation(callback, state, "абстрактная композиция")


async def process_image_generation(callback: CallbackQuery, state: FSMContext, style: str):
    """Обработка генерации изображения."""
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "")

    if generation_mode == "image_from_content":
        # Генерация на основе контента
        generated_content = data.get("generated_content", "")

        # Создаем промпт на основе контента
        prompt = f"На основе этого текста поста: '{generated_content[:200]}...' \n\nСоздай изображение в {style}."

    else:
        # Используем пользовательский промпт
        user_description = data.get("image_description", "")
        prompt = f"{user_description}. Стиль: {style}."

    await state.update_data(selected_style=style, final_prompt=prompt)

    # Запрашиваем размер изображения
    await callback.message.answer(
        f"✅ Выбран стиль: **{style}**\n\n"
        "📐 **Выберите размер изображения:**",
        reply_markup=get_image_size_inline_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_image_size)


# === ОБРАБОТЧИКИ ВЫБОРА РАЗМЕРА ИЗОБРАЖЕНИЯ ===
@callbacks_router.callback_query(F.data == "image_size_1024x1024")
async def image_size_1024x1024_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора размера 1024x1024."""
    await callback.answer()
    await generate_final_image(callback, state, 1024, 1024)


@callbacks_router.callback_query(F.data == "image_size_1200x630")
async def image_size_1200x630_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора размера 1200x630."""
    await callback.answer()
    await generate_final_image(callback, state, 1200, 630)


@callbacks_router.callback_query(F.data == "image_size_630x1200")
async def image_size_630x1200_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора размера 630x1200."""
    await callback.answer()
    await generate_final_image(callback, state, 630, 1200)


async def generate_final_image(callback: CallbackQuery, state: FSMContext, width: int, height: int):
    """Генерация финального изображения."""
    data = await state.get_data()
    prompt = data.get("final_prompt", "")

    await callback.message.answer(
        f"🎨 **Генерирую изображение...**\n\n"
        f"📝 Промпт: {prompt[:100]}...\n"
        f"📐 Размер: {width}x{height}\n\n"
        "_Это может занять 30-60 секунд..._",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Получаем сервис генерации изображений
        image_service = dp.get("image_generation_service")

        if not image_service:
            raise Exception("Сервис генерации изображений не настроен")

        # Генерируем изображение
        image_bytes = await image_service.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            images=1,
        )

        # Создаем файл для отправки
        from aiogram.types.input_file import BufferedInputFile
        image_file = BufferedInputFile(image_bytes, "generated_image.png")

        await callback.message.answer_photo(
            photo=image_file,
            caption="✅ **Изображение готово!**\n\nЧто вы хотите сделать дальше?",
            reply_markup=get_image_generation_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )

        await state.clear()

    except Exception as e:
        logger.exception("Ошибка при генерации изображения")
        await callback.message.answer(
            f"❌ **Ошибка генерации**\n\n"
            f"Не удалось сгенерировать изображение: {str(e)}\n\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=get_image_generation_keyboard(),
        )
        await state.clear()


# === ОБРАБОТЧИКИ СООБЩЕНИЙ ДЛЯ ОПИСАНИЯ ИЗОБРАЖЕНИЯ ===
@callbacks_router.message(ContentGeneration.waiting_for_image_description, F.text)
async def process_image_description(message: Message, state: FSMContext):
    """Обработка описания изображения."""
    description = message.text.strip()

    if not description:
        await message.answer("⚠️ Пожалуйста, опишите изображение.")
        return

    await state.update_data(image_description=description)
    await state.set_state(ContentGeneration.waiting_for_image_style)

    await message.answer(
        f"✅ Описание сохранено: **{description[:100]}...**\n\n"
        "🎭 **Выберите стиль генерации:**",
        reply_markup=get_image_style_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КЛАВИАТУР ===
def get_image_style_keyboard():
    """Получить клавиатуру выбора стиля изображения."""
    from bot.keyboards.inline import get_image_style_keyboard as func
    return func()


def get_image_size_inline_keyboard():
    """Получить клавиатуру выбора размера изображения."""
    from bot.keyboards.inline import get_image_size_inline_keyboard as func
    return func()


def get_image_generation_keyboard():
    """Получить клавиатуру генерации изображений."""
    from bot.keyboards.inline import get_image_generation_keyboard as func
    return func()


def get_image_source_keyboard():
    """Получить клавиатуру выбора источника изображения."""
    from bot.keyboards.inline import get_image_source_keyboard as func
    return func()


# === ОБРАБОТЧИКИ ДЛЯ КОНТЕНТ-ПЛАНА ===

@callbacks_router.callback_query(F.data == "period_3days")
async def period_3days_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора периода 3 дня."""
    await period_callback_handler(callback, state, "3 дня")


@callbacks_router.callback_query(F.data == "period_week")
async def period_week_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора периода неделя."""
    await period_callback_handler(callback, state, "Неделя")


@callbacks_router.callback_query(F.data == "period_month")
async def period_month_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора периода месяц."""
    await period_callback_handler(callback, state, "Месяц")


async def period_callback_handler(callback: CallbackQuery, state: FSMContext, period: str):
    """Общий обработчик для выбора периода контент-плана."""
    await callback.answer()
    await state.update_data(period=period)

    from bot.keyboards.inline import get_frequency_keyboard
    await callback.message.answer(
        "🔁 Какая частота публикаций должна быть?",
        reply_markup=get_frequency_keyboard(),
    )
    await state.set_state(ContentPlan.waiting_for_frequency)


@callbacks_router.callback_query(F.data == "period_custom")
async def period_custom_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора своего варианта периода."""
    await callback.answer()

    await callback.message.answer(
        "🖊️ Введите свой вариант периода.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlan.waiting_for_custom_period)


@callbacks_router.callback_query(F.data == "frequency_daily")
async def frequency_daily_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора частоты каждый день."""
    await frequency_callback_handler(callback, state, "каждый день")


@callbacks_router.callback_query(F.data == "frequency_every_two_days")
async def frequency_every_two_days_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора частоты раз в два дня."""
    await frequency_callback_handler(callback, state, "раз в два дня")


async def frequency_callback_handler(callback: CallbackQuery, state: FSMContext, frequency: str):
    """Общий обработчик для выбора частоты контент-плана."""
    await callback.answer()
    await state.update_data(frequency=frequency)

    await callback.message.answer(
        "📄 Теперь распишите, на какие темы должен быть ориентирован контент-план.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlan.waiting_for_themes)


@callbacks_router.callback_query(F.data == "frequency_custom")
async def frequency_custom_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора своего варианта частоты."""
    await callback.answer()

    await callback.message.answer(
        "🖊️ Введите свой вариант частоты публикаций.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlan.waiting_for_custom_frequency)


# === ОБРАБОТЧИКИ ВЫБОРА ИСТОЧНИКА ИЗОБРАЖЕНИЯ ===
@callbacks_router.callback_query(F.data == "image_source_ai")
async def image_source_ai_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора ИИ для генерации изображения."""
    await callback.answer()
    await image_source_handler_common(callback, state, "🤖 Сгенерировать ИИ")


@callbacks_router.callback_query(F.data == "image_source_upload")
async def image_source_upload_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора загрузки своего изображения."""
    await callback.answer()
    await image_source_handler_common(callback, state, "📎 Загрузить своё")


@callbacks_router.callback_query(F.data == "image_source_none")
async def image_source_none_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора без фото."""
    await callback.answer()
    await image_source_handler_common(callback, state, "🚫 Без фото")


# === ОБРАБОТЧИКИ ВЫБОРА ФОТО ДЛЯ КАРТОЧКИ ===
@callbacks_router.callback_query(F.data == "card_photo_ai")
async def card_photo_ai_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора ИИ для генерации фото карточки."""
    await callback.answer()
    await card_photo_handler_common(callback, state, "🤖 AI сгенерирует фото")


@callbacks_router.callback_query(F.data == "card_photo_upload")
async def card_photo_upload_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора загрузки своего фото для карточки."""
    await callback.answer()
    await card_photo_handler_common(callback, state, "📎 Загрузить своё фото")


@callbacks_router.callback_query(F.data == "card_photo_none")
async def card_photo_none_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора без фото для карточки."""
    await callback.answer()
    await card_photo_handler_common(callback, state, "🚫 Без фото")


@callbacks_router.callback_query(F.data == "back_to_confirmation")
async def back_to_confirmation_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к подтверждению генерации."""
    await callback.answer()
    from bot.keyboards.inline import get_post_generation_keyboard
    await callback.message.answer(
        "✨ Что хотите сделать дальше?",
        reply_markup=get_post_generation_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_confirmation)


@callbacks_router.callback_query(F.data == "back_to_platform")
async def back_to_platform_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору платформы."""
    await callback.answer()
    await callback.message.answer(
        "📱 **На какой платформе будет публиковаться пост?**",
        reply_markup=get_platform_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_platform)


@callbacks_router.message(ContentGeneration.waiting_for_image_prompt, F.text)
async def callback_image_prompt_handler(message: Message, state: FSMContext):
    """Обработчик для описания изображения ИИ в callbacks flow."""
    image_prompt = message.text.strip()
    if not image_prompt:
        await message.answer(
            "Пожалуйста, опишите желаемое изображение.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(image_prompt=image_prompt)

    # Переходим к генерации контента
    from bot.handlers.generation import complete_generation_handler
    await complete_generation_handler(message, state)


@callbacks_router.message(ContentGeneration.waiting_for_user_image, F.photo)
async def callback_user_image_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского изображения в callbacks flow."""
    if not message.photo:
        await message.answer(
            "Пожалуйста, загрузите изображение (фото).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Получаем наибольшее по размеру фото для лучшего качества
    photo = message.photo[-1]

    # Скачиваем изображение
    from app import dp
    bot = dp["bot"]

    try:
        image_file = await bot.download(photo.file_id, destination=None)
        image_bytes = image_file.read()

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке изображения: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


@callbacks_router.message(ContentGeneration.waiting_for_user_image, F.document)
async def callback_user_document_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского документа с изображением в callbacks flow."""
    if not message.document:
        return

    # Проверяем, что это изображение
    mime_type = message.document.mime_type
    if not mime_type or not mime_type.startswith('image/'):
        await message.answer(
            "Пожалуйста, отправьте файл с изображением (JPEG, PNG).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    from app import dp
    bot = dp["bot"]

    try:
        document_file = await bot.download(message.document.file_id, destination=None)
        image_bytes = document_file.read()

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с изображением: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


@callbacks_router.message(ContentGeneration.waiting_for_free_image_prompt, F.text)
async def callback_free_image_prompt_handler(message: Message, state: FSMContext):
    """Обработчик для описания изображения ИИ в free form callbacks flow."""
    image_prompt = message.text.strip()
    if not image_prompt:
        await message.answer(
            "Пожалуйста, опишите желаемое изображение.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(image_prompt=image_prompt)

    # Переходим к генерации контента
    from bot.handlers.generation import complete_generation_handler
    await complete_generation_handler(message, state)


@callbacks_router.message(ContentGeneration.waiting_for_free_user_image, F.photo)
async def callback_free_user_image_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского изображения в free form callbacks flow."""
    if not message.photo:
        await message.answer(
            "Пожалуйста, загрузите изображение (фото).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Получаем наибольшее по размеру фото для лучшего качества
    photo = message.photo[-1]

    # Скачиваем изображение
    from app import dp
    bot = dp["bot"]

    try:
        image_file = await bot.download(photo.file_id, destination=None)
        image_bytes = image_file.read()

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке изображения: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


@callbacks_router.message(ContentGeneration.waiting_for_free_user_image, F.document)
async def callback_free_user_document_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского документа с изображением в free form callbacks flow."""
    if not message.document:
        return

    # Проверяем, что это изображение
    mime_type = message.document.mime_type
    if not mime_type or not mime_type.startswith('image/'):
        await message.answer(
            "Пожалуйста, отправьте файл с изображением (JPEG, PNG).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    from app import dp
    bot = dp["bot"]

    try:
        document_file = await bot.download(message.document.file_id, destination=None)
        image_bytes = document_file.read()

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с изображением: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


async def image_source_handler_common(callback: CallbackQuery, state: FSMContext, image_source: str):
    """Общий обработчик для выбора источника изображения."""
    await state.update_data(image_source=image_source)

    if image_source == "🤖 Сгенерировать ИИ":
        # Переходим к генерации ИИ
        await callback.message.answer(
            "🎨 **Опишите желаемую картинку для карточки**\n"
            "Опишите, как должна выглядеть иллюстрация к вашему посту. "
            "Можете упомянуть стиль, цвета, настроение.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_image_prompt)
    elif image_source == "📎 Загрузить своё":
        await callback.message.answer(
            "📎 **Загрузите изображение**\n"
            "Пришлите фотографию или изображение, которое будет использовано в карточке. "
            "Поддерживаемые форматы: JPEG, PNG.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_user_image)
    else:  # "🚫 Без фото"
        await callback.message.answer(
            "✅ **Выбрано: Без фото**\n"
            "🎨 Создаем контент без изображения...",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Переходим к генерации контента без фото
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(callback.message, state)


async def free_image_source_handler_common(callback: CallbackQuery, state: FSMContext, image_source: str):
    """Общий обработчик для выбора источника изображения в free form."""
    await state.update_data(image_source=image_source)

    if image_source == "🤖 Сгенерировать ИИ":
        # Переходим к генерации ИИ для free form
        await callback.message.answer(
            "🎨 **Опишите желаемую картинку для карточки**\n"
            "Опишите, как должна выглядеть иллюстрация к вашему посту. "
            "Можете упомянуть стиль, цвета, настроение.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_free_image_prompt)
    elif image_source == "📎 Загрузить своё":
        await callback.message.answer(
            "📎 **Загрузите изображение**\n"
            "Пришлите фотографию или изображение, которое будет использовано в карточке. "
            "Поддерживаемые форматы: JPEG, PNG.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_free_user_image)
    else:  # "🚫 Без фото"
        await callback.message.answer(
            "✅ **Выбрано: Без фото**\n"
            "🎨 Создаем контент без изображения...",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Переходим к генерации контента без фото
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(callback.message, state)


async def card_photo_handler_common(callback: CallbackQuery, state: FSMContext, card_source: str):
    """Общий обработчик для выбора источника фото для карточки."""
    await state.update_data(card_image_source=card_source)

    if card_source == "🤖 AI сгенерирует фото":
        # Переходим к запросу промпта для генерации фото карточки
        await callback.message.answer(
            "🎨 **Опишите желаемое фото для карточки**\n"
            "Опишите, какое фото должно быть на карточке. "
            "Можете упомянуть тему, композицию, стиль.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_card_photo_prompt)
    elif card_source == "📎 Загрузить своё фото":
        await callback.message.answer(
            "📎 **Загрузите фото для карточки**\n"
            "Пришлите фотографию, которая будет использована в карточке. "
            "Поддерживаемые форматы: JPEG, PNG.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_card_user_photo)
    else:  # "🚫 Без фото"
        await state.update_data(card_image_source="🚫 Без фото")
        await callback.message.answer(
            "✅ **Выбрано: Без фото для карточки**\n"
            "🎨 Переходим к генерации карточек...",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Переходим к генерации карточек без фото
        from bot.handlers.generation import generate_cards_handler
        await generate_cards_handler(callback.message, state)


@callbacks_router.message(ContentGeneration.waiting_for_card_photo_prompt, F.text)
async def handle_card_photo_prompt(message: Message, state: FSMContext):
    """Обработчик для описания фото карточки."""
    card_prompt = message.text.strip()
    if not card_prompt:
        await message.answer(
            "Пожалуйста, опишите желаемое фото для карточки.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(card_image_prompt=card_prompt)

    # Переходим к генерации карточек
    from bot.handlers.generation import generate_cards_handler
    await generate_cards_handler(message, state)


@callbacks_router.message(ContentGeneration.waiting_for_card_user_photo, F.photo)
async def handle_card_user_photo(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского фото для карточки."""
    if not message.photo:
        await message.answer(
            "Пожалуйста, загрузите изображение (фото).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Получаем наибольшее по размеру фото для лучшего качества
    photo = message.photo[-1]

    # Скачиваем изображение
    from app import dp
    bot = dp["bot"]

    try:
        image_file = await bot.download(photo.file_id, destination=None)
        image_bytes = image_file.read()

        await state.update_data(card_user_image=image_bytes)

        await message.answer(
            "✅ Фото для карточки загружено!\n"
            "🎨 Создаем карточки с вашим фото...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации карточек
        from bot.handlers.generation import generate_cards_handler
        await generate_cards_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке фото для карточки: {e}")
        await message.answer(
            "❌ Ошибка при загрузке фото. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


@callbacks_router.message(ContentGeneration.waiting_for_card_user_photo, F.document)
async def handle_card_user_document(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского документа с фото для карточки."""
    if not message.document:
        return

    # Проверяем, что это изображение
    mime_type = message.document.mime_type
    if not mime_type or not mime_type.startswith('image/'):
        await message.answer(
            "Пожалуйста, отправьте файл с изображением (JPEG, PNG).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    from app import dp
    bot = dp["bot"]

    try:
        document_file = await bot.download(message.document.file_id, destination=None)
        image_bytes = document_file.read()

        await state.update_data(card_user_image=image_bytes)

        await message.answer(
            "✅ Фото для карточки загружено!\n"
            "🎨 Создаем карточки с вашим фото...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации карточек
        from bot.handlers.generation import generate_cards_handler
        await generate_cards_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с фото для карточки: {e}")
        await message.answer(
            "❌ Ошибка при загрузке фото. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


# === ДОБАВЛЕННЫЕ ОБРАБОТЧИКИ КОНТЕНТ-ПЛАНА ===
# TODO: Эти обработчики нужно добавить в content_plan.py как message handlers
# Сейчас они удалены из callbacks.py, поскольку @callbacks_router.callback_query не подходит для текстовых сообщений
