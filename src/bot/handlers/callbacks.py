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







# === ОБРАБОТЧИКИ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ ===



