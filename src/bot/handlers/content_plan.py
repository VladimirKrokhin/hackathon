import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.enums.parse_mode import ParseMode

from app import dp
from bot.states import ContentPlan
from bot.keyboards.inline import (
    get_period_keyboard,
    get_frequency_keyboard,
    get_skip_keyboard,
)
from services.content_generation import TextContentGenerationService

# Константы для контент-плана
PERIOD_OPTIONS = ["3 дня", "Неделя", "Месяц"]
FREQUENCY_OPTIONS = ["каждый день", "раз в два дня"]
CUSTOM_OPTION = "🖊️ Свой вариант"
SKIP_OPTION = "⏩ Пропустить"

content_plan_router = Router(name="content_plan")
logger = logging.getLogger(__name__)


@content_plan_router.message(Command("contentplan"))
async def start_content_plan(message: Message, state: FSMContext):
    await message.answer(
        "📅 Давайте создадим контент-план для ваших постов!\n\n"
        "На какой период вы хотите подготовить план?",
        reply_markup=get_period_keyboard(),
    )
    await state.set_state(ContentPlan.waiting_for_period)


# === MESSAGE HANDLERS для обработки текстового ввода ===

@content_plan_router.message(ContentPlan.waiting_for_custom_period, F.text)
async def custom_period_message_handler(message: Message, state: FSMContext):
    """Обработчик ввода своего варианта периода."""
    period = message.text.strip()
    if not period:
        await message.answer(
            "Пожалуйста, отправьте текст с вашим вариантом периода.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(period=period)

    from bot.keyboards.inline import get_frequency_keyboard
    await message.answer(
        "🔁 Какая частота публикаций должна быть?",
        reply_markup=get_frequency_keyboard(),
    )
    await state.set_state(ContentPlan.waiting_for_frequency)


@content_plan_router.message(ContentPlan.waiting_for_custom_frequency, F.text)
async def custom_frequency_message_handler(message: Message, state: FSMContext):
    """Обработчик ввода своей частоты публикаций."""
    frequency = message.text.strip()
    if not frequency:
        await message.answer(
            "Пожалуйста, отправьте текст с вашим вариантом частоты публикаций.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(frequency=frequency)

    await message.answer(
        "📄 Теперь распишите, на какие темы должен быть ориентирован контент-план.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlan.waiting_for_themes)


@content_plan_router.message(ContentPlan.waiting_for_themes, F.text)
async def themes_message_handler(message: Message, state: FSMContext):
    """Обработчик ввода тем для контент-плана."""
    themes = message.text.strip()
    await state.update_data(themes=themes)

    from bot.keyboards.inline import get_skip_keyboard
    await message.answer(
        "🖋️ Укажите дополнительную информацию или требования.",
        reply_markup=get_skip_keyboard(),
    )
    await state.set_state(ContentPlan.waiting_for_details)


@content_plan_router.message(ContentPlan.waiting_for_details, F.text)
async def details_message_handler(message: Message, state: FSMContext):
    """Обработчик ввода деталей для контент-плана."""
    details = message.text.strip()
    if details == "⏩ Пропустить":
        details = ""
    await state.update_data(details=details)

    data = await state.get_data()

    await message.answer(
        "🧠 Генерирую контент-план...",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        text_generation_service: TextContentGenerationService = dp["text_content_generation_service"]
        generated_plan = await text_generation_service.generate_content_plan(data)

        await message.answer(
            f"✅ Ваш сгенерированный контент-план:",
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer(
            generated_plan,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardRemove(),
        )

        await state.clear()

    except Exception as error:
        logger.exception("Ошибка при генерации контент-плана: %s", error)
        await message.answer(
            "⚠️ Не удалось получить ответ.",
            reply_markup=ReplyKeyboardRemove(),
        )
        raise error


# === CALLBACK HANDLERS для обработки кнопок ===

@content_plan_router.callback_query(F.data == "period_3days")
async def period_3days_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора периода 3 дня."""
    await period_callback_handler(callback, state, "3 дня")


@content_plan_router.callback_query(F.data == "period_week")
async def period_week_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора периода неделя."""
    await period_callback_handler(callback, state, "Неделя")


@content_plan_router.callback_query(F.data == "period_month")
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


@content_plan_router.callback_query(F.data == "period_custom")
async def period_custom_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора своего варианта периода."""
    await callback.answer()

    await callback.message.answer(
        "🖊️ Введите свой вариант периода.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlan.waiting_for_custom_period)


@content_plan_router.callback_query(F.data == "frequency_daily")
async def frequency_daily_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора частоты каждый день."""
    await frequency_callback_handler(callback, state, "каждый день")


@content_plan_router.callback_query(F.data == "frequency_every_two_days")
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


@content_plan_router.callback_query(F.data == "frequency_custom")
async def frequency_custom_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора своего варианта частоты."""
    await callback.answer()

    await callback.message.answer(
        "🖊️ Введите свой вариант частоты публикаций.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlan.waiting_for_custom_frequency)


@content_plan_router.callback_query(F.data == "skip_step")
async def skip_step_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска шага."""
    await callback.answer()

    # Если мы в состоянии ожидания деталей, пропустить детали
    current_state = await state.get_state()
    if current_state == ContentPlan.waiting_for_details:
        await state.update_data(details="")

        data = await state.get_data()

        await callback.message.answer(
            "🧠 Генерирую контент-план...",
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            text_generation_service: TextContentGenerationService = dp["text_content_generation_service"]
            generated_plan = await text_generation_service.generate_content_plan(data)

            await callback.message.answer(
                f"✅ Ваш сгенерированный контент-план:",
                reply_markup=ReplyKeyboardRemove(),
            )
            await callback.message.answer(
                generated_plan,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=ReplyKeyboardRemove(),
            )

            await state.clear()

        except Exception as error:
            logger.exception("Ошибка при генерации контент-плана: %s", error)
            await callback.message.answer(
                "⚠️ Не удалось получить ответ.",
                reply_markup=ReplyKeyboardRemove(),
            )
            raise error


@content_plan_router.callback_query(F.data == "back_to_previous")
async def back_to_previous_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к предыдущему шагу или главное меню."""
    await callback.answer()
    await state.clear()
    from bot.handlers.start import start_handler
    await start_handler(callback.message, state)


# Конец файла
