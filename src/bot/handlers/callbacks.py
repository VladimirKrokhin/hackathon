import logging

from aiogram import Router, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message, ReplyKeyboardRemove

from bot.states import ContentGeneration, ContentPlan, NGOInfo, EditText

from bot import dispatcher, bot
from services.image_generation import ImageGenerationService
from services.ngo_service import NGOService


callbacks_router = Router(name="callbacks")
logger = logging.getLogger(__name__)



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
    from bot.handlers.start import start_handler

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



# === ОБРАБОТЧИКИ ВЫБОРА СТИЛЯ ПОВЕСТВОВАНИЯ ===
async def narrative_style_handler_common(callback: CallbackQuery, state: FSMContext, style_name: str):
    """Общий обработчик для всех стилей повествования."""
    await state.update_data(narrative_style=style_name)

    data = await state.get_data()
    generation_mode = data.get("generation_mode", "")

    if generation_mode == "free_form":
        # Для свободной формы - сразу переходим к выбору платформы
        await callback.message.answer(
            "📱 **На какой платформе будет публиковаться пост?**",
            reply_markup=PLATFORM_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_platform)
    else:
        # Для структурированной формы - сразу переходим к выбору платформы
        await callback.message.answer(
            "📱 **На какой платформе будет публиковаться пост?**",
            reply_markup=PLATFORM_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_platform)








# === ОБРАБОТЧИКИ ВЫБОРА ПЛАТФОРМЫ ===






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




# === ОБРАБОТЧИКИ ДЛЯ НКО ПРОЦЕССА ===
@callbacks_router.callback_query(F.data == "ngo_cancel")
async def ngo_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены процесса НКО."""
    await callback.answer()
    await state.clear()
    from bot.handlers.start import BACK_TO_START_KEYBOARD

    await callback.message.answer(
        "❎ Процесс сбора информации об НКО отменен.",
        reply_markup=BACK_TO_START_KEYBOARD,
    )


@callbacks_router.callback_query(F.data == "ngo_skip")
async def ngo_skip_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска шага в процессе НКО."""
    await callback.answer()

    current_state = await state.get_state()

    if current_state == NGOInfo.waiting_for_ngo_description:
        await state.update_data(ngo_description="Не указано")
        await callback.message.answer(
            f"✅ Описание: Не указано\n\n"
            "🎯 Какие формы деятельности ведет ваша НКО? (например: благотворительность, просвещение, помощь животным и т.д.)\n\n"
            "Можете перечислить через запятую или нажать ⏩ Пропустить.",
            reply_markup=NGO_NAVIGATION_KEYBOARD,
        )
        await state.set_state(NGOInfo.waiting_for_ngo_activities)

    elif current_state == NGOInfo.waiting_for_ngo_activities:
        await state.update_data(ngo_activities="Не указано")
        await callback.message.answer(
            f"✅ Формы деятельности: Не указано\n\n"
            "📞 Укажите контактную информацию для связи (телефон, email, сайт или социальные сети)\n\n"
            "Можете указать любые удобные способы связи или нажать ⏩ Пропустить.",
            reply_markup=NGO_NAVIGATION_KEYBOARD,
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
            reply_markup=NGO_NAVIGATION_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(NGOInfo.waiting_for_ngo_confirmation)



# === ОБРАБОТЧИКИ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ ===



