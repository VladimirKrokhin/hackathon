import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.enums.parse_mode import ParseMode

from app import dp
from bot.states import ContentPlan
from bot.keyboards.reply import (
    PERIOD_OPTIONS,
    FREQUENCY_OPTIONS,
    CUSTOM_OPTION,
    SKIP_OPTION,
    get_period_keyboard,
    get_frequency_keyboard,
    get_skip_keyboard,
)
from services.content_generation import TextContentGenerationService


content_plan_router = Router(name="content_plan")
logger = logging.getLogger(__name__)


@content_plan_router.message(Command("contentplan"))
async def start_content_plan(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📅 Давате создадим контент-план для ваших постов!\n\n"
        "На какой период вы хотите подготовить план?",
        reply_markup=get_period_keyboard(),
    )
    await state.set_state(ContentPlan.waiting_for_period)


@content_plan_router.message(ContentPlan.waiting_for_period, F.text)
async def period_handler(message: Message, state: FSMContext):
    period = message.text.strip()
    if period == CUSTOM_OPTION:
        await message.answer(
            "Введите свой вариант периода.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(ContentPlan.waiting_for_custom_period)
        return
    elif period not in PERIOD_OPTIONS:
        await message.answer(
            "Пожалуйста, выберите что-то из предложенных вариантов.",
            reply_markup=get_period_keyboard(),
        )
        return

    await state.update_data(period=period)

    await message.answer(
        "🔁 Какая частота публикаций должна быть?",
        reply_markup=get_frequency_keyboard(),
    )
    await state.set_state(ContentPlan.waiting_for_frequency)


@content_plan_router.message(ContentPlan.waiting_for_custom_period, F.text)
async def custom_period_handler(message: Message, state: FSMContext):
    period = message.text.strip()
    if not period:
        await message.answer("Пожалуйста, отправьте текст с вашим вариантом периода.")
        return

    await state.update_data(period=period)

    await message.answer(
        "🔁 Какая частота публикаций должна быть?",
        reply_markup=get_frequency_keyboard(),
    )
    await state.set_state(ContentPlan.waiting_for_frequency)


@content_plan_router.message(ContentPlan.waiting_for_frequency, F.text)
async def frequency_handler(message: Message, state: FSMContext):
    frequency = message.text.strip()

    if frequency == CUSTOM_OPTION:
        await message.answer(
            "Введите свой вариант частоты публикаций.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(ContentPlan.waiting_for_custom_frequency)
        return
    elif frequency not in FREQUENCY_OPTIONS:
        await message.answer(
            "Пожалуйста, выберите что-то из предложенных вариантов.",
            reply_markup=get_frequency_keyboard(),
        )
        return

    await state.update_data(frequency=frequency)

    await message.answer(
        "📄 Теперь распишите, на какие темы должен быть ориентирован контент-план.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlan.waiting_for_themes)


@content_plan_router.message(ContentPlan.waiting_for_custom_frequency, F.text)
async def custom_period_handler(message: Message, state: FSMContext):
    frequency = message.text.strip()
    if not frequency:
        await message.answer("Пожалуйста, отправьте текст с вашим вариантом частоты публикаций.")
        return

    await state.update_data(frequency=frequency)

    await message.answer(
        "📄 Теперь распишите, на какие темы должен быть ориентирован контент-план.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlan.waiting_for_themes)


@content_plan_router.message(ContentPlan.waiting_for_themes, F.text)
async def themes_handler(message: Message, state: FSMContext):
    themes = message.text.strip()
    await state.update_data(themes=themes)

    await message.answer(
        "🖋️ Укажите дополнительную информацию или требования.",
        reply_markup=get_skip_keyboard(),
    )
    await state.set_state(ContentPlan.waiting_for_details)


@content_plan_router.message(ContentPlan.waiting_for_details, F.text)
async def details_handler(message: Message, state: FSMContext):
    details = message.text.strip()
    if details == SKIP_OPTION:
        details = ""
    await state.update_data(details=details)

    data = await state.get_data()

    await message.answer("🧠 Генерирую контент-план...")

    try:
        text_generation_service: TextContentGenerationService = dp["text_content_generation_service"]
        generated_plan = await text_generation_service.generate_content_plan(data)
        await state.update_data(generated_plan=generated_plan)
    except Exception as error:
        logger.exception("Ошибка при генерации плана: %s", error)
        await message.answer(
            "⚠️ Не удалось получить ответ."
        )
        raise error

    await message.answer(
        f"✅ Ваш сгенерированный конетн-план:",
    )
    await message.answer(generated_plan, parse_mode=ParseMode.MARKDOWN)

    await state.clear()
