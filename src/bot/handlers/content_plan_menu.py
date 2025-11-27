import logging
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from services.content_plan_service import ContentPlanService

from bot import dispatcher

from models import ContentPlan

from bot.states import ContentPlan as ContentPlanState

from bot.handlers.content_plan_generation import PUBLICATION_TIME_INTERVAL_KEYBOARD

logger = logging.getLogger(__name__)
content_plan_menu_router = Router(name="content_plan_menu")

VIEW_USER_CONTENT_PLANS_CALLBACK_DATA = "content_plan_view"
CONTENT_PLAN_MENU_CALLBACK_DATA = "content_plan"
CREATE_NEW_CONTENT_PLAN_CALLBACK_DATA = "content_plan_create"

CONTENT_PLAN_MENU_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Посмотреть мои планы", callback_data=VIEW_USER_CONTENT_PLANS_CALLBACK_DATA)],
        [InlineKeyboardButton(text="➕ Создать новый план", callback_data=CREATE_NEW_CONTENT_PLAN_CALLBACK_DATA)],
        [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="content_plan_back")],
    ]
)


CONTENT_PLAN_LIST_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        # Кнопка создания нового плана
        [InlineKeyboardButton(text="➕ Создать новый план", callback_data=CREATE_NEW_CONTENT_PLAN_CALLBACK_DATA)],
        # Кнопка возврата
        [InlineKeyboardButton(text="⬅️ Назад в меню контент-планов", callback_data=CONTENT_PLAN_MENU_CALLBACK_DATA)],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="content_plan_back")],
    ]
)



# FIXME: Этот обработчик используется
@content_plan_menu_router.callback_query(F.data == CONTENT_PLAN_MENU_CALLBACK_DATA)
async def content_plan_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Показать меню управления контент-планами."""
    await callback.answer()
    await state.clear()
    
    # Получаем количество планов пользователя
    content_plan_service: ContentPlanService = dispatcher["content_plan_service"]
    user_id = callback.from_user.id
    
    plans: tuple[ContentPlan, ...] = await content_plan_service.get_user_plans(user_id)
    plans_count = len(plans)

    text = (
        f"📅 *Управление контент-планами*\n\n"
        f"📊 У вас создано планов: {plans_count}\n\n"
        f"Выберите действие:"
    )

    await callback.message.answer(
        text=text,
        reply_markup=CONTENT_PLAN_MENU_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN
    )



        
# FIXME: этот колбэк используется
@content_plan_menu_router.callback_query(F.data == CREATE_NEW_CONTENT_PLAN_CALLBACK_DATA)
async def create_content_plan_handler(callback: CallbackQuery, state: FSMContext):
    """Начать создание нового контент-плана."""
    await callback.answer()
    
    await callback.message.answer(
        "📅 Давайте создадим контент-план для ваших постов!\n\n"
        "На какой период вы хотите подготовить план?",
        reply_markup=PUBLICATION_TIME_INTERVAL_KEYBOARD,
    )
    await state.set_state(ContentPlanState.waiting_for_period)

# FIXME: Этот колбэк используется
@content_plan_menu_router.callback_query(F.data == VIEW_USER_CONTENT_PLANS_CALLBACK_DATA)
async def view_content_plans_handler(callback: CallbackQuery, state: FSMContext):
    """Показать список существующих планов пользователя."""
    await callback.answer()
    
    content_plan_service: ContentPlanService = dispatcher["content_plan_service"]
    user_id: int = callback.from_user.id
    
    plans = await content_plan_service.get_user_plans(user_id)

    text = "📋 *Ваши контент-планы*\n\n"

    if not plans:
        text += (
            "У вас пока нет созданных контент-планов.\n"
            "Создайте первый план, нажав кнопку ниже:"
        )

        await callback.message.answer(
            text=text,
            # FIXME: Поменяй на другую клавиатуру, где можно только вернуться назад
            reply_markup=CONTENT_PLAN_MENU_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )

    else:
        # FIXME: Добавь пагинацию


        for i, plan in enumerate(plans, 1):
            text += (
                f"{i}. *{plan.plan_name}*\n"
                f"   📅 Период: {plan.period}\n"
                f"   🆔 ID: `{plan.id_}`\n\n"
            )

        text += "Выберите план для управления:"

        list_keyboard = CONTENT_PLAN_LIST_KEYBOARD.model_copy(deep=True)

        # FIXME: коллбэки не обрабатываются
        for plan in plans:
            button_text = f"{plan.plan_name}"
            callback_data = f"content_plan_manage_{plan.id_}"
            list_keyboard.inline_keyboard.insert(
                0,
                [InlineKeyboardButton(text=button_text, callback_data=callback_data)],
            )


        await callback.message.answer(
            text=text,
            reply_markup=list_keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        

# === НАВИГАЦИЯ ===
@content_plan_menu_router.callback_query(F.data == "content_plan_back")
async def back_to_start_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""

    from bot.handlers.start import start_handler

    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


@content_plan_menu_router.callback_query(F.data == "skip_step")
async def skip_step_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска шага."""
    await callback.answer()
    await callback.message.answer(
        "Шаг пропущен.",
        reply_markup=ReplyKeyboardRemove(),
    )


@content_plan_menu_router.callback_query(F.data == "done")
async def done_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик завершения процесса."""
    from bot.handlers.start import start_handler

    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)















