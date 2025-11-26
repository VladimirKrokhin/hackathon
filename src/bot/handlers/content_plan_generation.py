import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums.parse_mode import ParseMode

from bot import dispatcher
from bot.states import ContentPlan as ContentPlanState
from services.notification_service import NotificationService
from services.text_generation import TextGenerationService
from services.content_plan_service import ContentPlanService

from dtos import PlanPromptContext

from models import ContentPlan

THREE_DAYS_PUBLICATION_TIME_PERIOD = "period_3days"
WEEK_PUBLICATION_TIME_PERIOD = "period_week"
MONTH_PUBLICATION_TIME_PERIOD = "period_month"

PUBLICATION_TIME_PERIOD_CALLBACKS = {
    THREE_DAYS_PUBLICATION_TIME_PERIOD,
    WEEK_PUBLICATION_TIME_PERIOD,
    MONTH_PUBLICATION_TIME_PERIOD
}

CUSTOM_PUBLICATION_TIME_PERIOD = "period_custom"

PUBLICATION_TIME_INTERVAL_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="3 дня", callback_data=THREE_DAYS_PUBLICATION_TIME_PERIOD)],
        [InlineKeyboardButton(text="Неделя", callback_data=WEEK_PUBLICATION_TIME_PERIOD)],
        [InlineKeyboardButton(text="Месяц", callback_data=MONTH_PUBLICATION_TIME_PERIOD)],
        [InlineKeyboardButton(text="🖊️ Свой вариант", callback_data=CUSTOM_PUBLICATION_TIME_PERIOD)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
    ]
)

logger = logging.getLogger(__name__)

# Константы для контент-плана
PERIOD_OPTIONS = ["3 дня", "Неделя", "Месяц"]
FREQUENCY_OPTIONS = ["каждый день", "раз в два дня"]
CUSTOM_OPTION = "🖊️ Свой вариант"
SKIP_OPTION = "⏩ Пропустить"

content_plan_router = Router(name="content_plan")


DAILY_PUBLICATION_FREQUENCY = "frequency_daily"
ONCE_PER_TWO_DAYS_PUBLICATION_FREQUENCY = "frequency_every_two_days"


PUBLICATION_FREQUENCY_KEYBOARD = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="каждый день", callback_data=DAILY_PUBLICATION_FREQUENCY)],
            [InlineKeyboardButton(text="раз в два дня", callback_data=ONCE_PER_TWO_DAYS_PUBLICATION_FREQUENCY)],
            [InlineKeyboardButton(text="🖊️ Свой вариант", callback_data="frequency_custom")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
        ]
    )

# SKIP_KEYBOARD = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text=f"⏩ Пропустить", callback_data="skip_step")],
#             [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
#         ]
#     )


# FIXME: не работает, пока не изменен ContentPlanService.generate_content_plan на возврат экземпляра ContentPlan вместо str
async def generate_and_save_plan(message: Message, state: FSMContext, data: dict) -> None:
    """
    Общая функция для генерации и сохранения контент-плана
    """
    content_plan_service: ContentPlanService = dispatcher["content_plan_service"]

    await message.answer(
        "🧠 Генерирую контент-план...",
        reply_markup=ReplyKeyboardRemove(),
    )

    generate_plan_context = PlanPromptContext.from_dict(data)

    generated_plan: ContentPlan = await content_plan_service.generate_content_plan(generate_plan_context)

    await message.answer(
        "Ваш контент-план:",
        reply_markup=ReplyKeyboardRemove(),
    )

    # TODO: Правильно распарси контент-план в текстовое представление
    # TODO: для пользователя и сначала запроси у пользователя подтверждение

    await message.answer(
        str(generated_plan),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
    )

    # Сохраняем план в базу данных
    plan_id = await content_plan_service.save_content_plan(
        generated_plan
    )

    # Отправляем план пользователю
    await message.answer(
        f"✅ Ваш контент-план создан и сохранен!",
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.clear()








# FIXME: дублирует, нужен ли?
@content_plan_router.message(ContentPlanState.waiting_for_custom_frequency, F.text)
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
    await state.set_state(ContentPlanState.waiting_for_themes)


@content_plan_router.message(ContentPlanState.waiting_for_themes, F.text)
async def themes_message_handler(message: Message, state: FSMContext):
    """Обработчик ввода тем для контент-плана."""
    themes = message.text.strip()
    await state.update_data(themes=themes)

    await message.answer(
        "🖋️ Укажите дополнительную информацию или требования.",
        # FIXME: Добавь кнопку пропустить
        # reply_markup=SKIP_KEYBOARD,
    )
    await state.set_state(ContentPlanState.waiting_for_details)


@content_plan_router.message(ContentPlanState.waiting_for_details, F.text)
async def details_message_handler(message: Message, state: FSMContext):
    """Обработчик ввода деталей для контент-плана."""
    details = message.text.strip()

    await state.update_data(details=details)

    data = await state.get_data()
    await generate_and_save_plan(message, state, data)


# Выбор частоты периода публикации

async def general_period_handler(message: Message, state: FSMContext, period: str):
    await state.update_data(period=period)

    await message.answer(
        "🔁 Какая частота публикаций должна быть?",
        reply_markup=PUBLICATION_FREQUENCY_KEYBOARD,
    )
    await state.set_state(ContentPlanState.waiting_for_frequency)

# FIXME: этот обработчик используется
@content_plan_router.callback_query(F.data.in_(PUBLICATION_TIME_PERIOD_CALLBACKS))
async def period_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора периода 3 дня."""
    PERIODS_MAPPING = {
        THREE_DAYS_PUBLICATION_TIME_PERIOD: "3 дня",
        WEEK_PUBLICATION_TIME_PERIOD: "Неделя",
        MONTH_PUBLICATION_TIME_PERIOD: "Месяц"
    }
    callback_data = callback.data
    period = PERIODS_MAPPING[callback_data]

    await general_period_handler(callback.message, state, period)
    await callback.answer()

# FIXME: Этот обработчик используется
@content_plan_router.callback_query(F.data == CUSTOM_PUBLICATION_TIME_PERIOD)
async def period_custom_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора своего варианта периода."""
    await callback.message.answer(
        "🖊️ Введите свой вариант периода.",
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.set_state(ContentPlanState.waiting_for_custom_period)
    await callback.answer()

# FIXME: Этот обработчик используется
@content_plan_router.message(ContentPlanState.waiting_for_custom_period, F.text)
async def custom_period_message_handler(message: Message, state: FSMContext):
    """Обработчик ввода своего варианта периода."""
    period = message.text.strip()
    if not period:
        await message.answer(
            "Пожалуйста, отправьте текст с вашим вариантом периода.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await general_period_handler(message, state, period)


# Выбор частоты публикации

@content_plan_router.callback_query(F.data == DAILY_PUBLICATION_FREQUENCY)
async def frequency_daily_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора частоты каждый день."""
    await frequency_callback_handler(callback, state, "каждый день")


@content_plan_router.callback_query(F.data == ONCE_PER_TWO_DAYS_PUBLICATION_FREQUENCY)
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
    await state.set_state(ContentPlanState.waiting_for_themes)


@content_plan_router.callback_query(F.data == "frequency_custom")
async def frequency_custom_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора своего варианта частоты."""
    await callback.answer()

    await callback.message.answer(
        "🖊️ Введите свой вариант частоты публикаций.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentPlanState.waiting_for_custom_frequency)


@content_plan_router.callback_query(F.data == "skip_step")
async def skip_step_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска шага."""
    await callback.answer()

    # Если мы в состоянии ожидания деталей, пропустить детали
    current_state = await state.get_state()
    if current_state == ContentPlanState.waiting_for_details:
        await state.update_data(details="")
        data = await state.get_data()
        await generate_and_save_plan(callback.message, state, data)


@content_plan_router.callback_query(F.data == "back_to_previous")
async def back_to_previous_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к предыдущему шагу или главное меню."""
    await callback.answer()
    await state.clear()
    from bot.handlers.start import start_handler
    await start_handler(callback.message, state)
