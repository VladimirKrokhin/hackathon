import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.app import dp
from bot.keyboards.inline import get_content_plan_menu_keyboard, get_main_menu_keyboard
from services.content_plan_service import ContentPlanService

logger = logging.getLogger(__name__)
content_plan_menu_router = Router(name="content_plan_menu")


@content_plan_menu_router.callback_query(F.data == "content_plan")
async def content_plan_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Показать меню управления контент-планами."""
    await callback.answer()
    await state.clear()
    
    # Получаем количество планов пользователя
    content_plan_service: ContentPlanService = dp["content_plan_service"]
    user_id = callback.from_user.id
    
    try:
        plans = await content_plan_service.get_user_plans(user_id)
        plans_count = len(plans) if plans else 0
        
        text = f"📅 *Управление контент-планами*\n\n"
        text += f"📊 У вас создано планов: {plans_count}\n\n"
        text += f"Выберите действие:"
        
        if callback.message.photo:
            # Если сообщение содержит фото, отправляем новое сообщение
            await callback.message.answer(
                text=text,
                reply_markup=get_content_plan_menu_keyboard(plans_count > 0),
                parse_mode="Markdown"
            )
        else:
            # Если сообщение содержит текст, редактируем его
            await callback.message.edit_text(
                text=text,
                reply_markup=get_content_plan_menu_keyboard(plans_count > 0),
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logger.error(f"Ошибка при получении планов пользователя {user_id}: {e}")
        if callback.message.photo:
            await callback.message.answer(
                "⚠️ Произошла ошибка при загрузке данных.\n\nВыберите действие:",
                reply_markup=get_content_plan_menu_keyboard(False)
            )
        else:
            await callback.message.edit_text(
                "⚠️ Произошла ошибка при загрузке данных.\n\nВыберите действие:",
                reply_markup=get_content_plan_menu_keyboard(False)
            )


@content_plan_menu_router.callback_query(F.data == "content_plan_create")
async def create_content_plan_handler(callback: CallbackQuery, state: FSMContext):
    """Начать создание нового контент-плана."""
    await callback.answer()
    
    # Перенаправляем к существующему обработчику создания планов
    from bot.handlers.content_plan import start_content_plan
    await start_content_plan(callback.message, state)


@content_plan_menu_router.callback_query(F.data == "content_plan_view")
async def view_content_plans_handler(callback: CallbackQuery, state: FSMContext):
    """Показать список существующих планов пользователя."""
    await callback.answer()
    
    content_plan_service: ContentPlanService = dp["content_plan_service"]
    user_id = callback.from_user.id
    
    try:
        plans = await content_plan_service.get_user_plans(user_id)
        
        if not plans:
            text = "📋 *Ваши контент-планы*\n\n"
            text += "У вас пока нет созданных контент-планов.\n"
            text += "Создайте первый план, нажав кнопку ниже:"
            
            await callback.message.edit_text(
                text=text,
                reply_markup=get_content_plan_menu_keyboard(False),
                parse_mode="Markdown"
            )
            return
        
        # Формируем список планов
        text = "📋 *Ваши контент-планы:*\n\n"
        
        for i, plan in enumerate(plans, 1):
            status_emoji = "✅" if plan.is_active else "⏸️"
            status_text = "активен" if plan.is_active else "приостановлен"
            
            text += f"{i}. *{plan.plan_name}*\n"
            text += f"   📊 Статус: {status_emoji} {status_text}\n"
            text += f"   📅 Период: {plan.period}\n"
            text += f"   🆔 ID: `{plan.id}`\n\n"
        
        text += "Выберите план для управления:"
        
        await callback.message.edit_text(
            text=text,
            reply_markup=get_content_plan_list_keyboard(plans),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении планов пользователя {user_id}: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при загрузке планов.",
            reply_markup=get_content_plan_menu_keyboard(False)
        )


@content_plan_menu_router.callback_query(F.data == "content_plan_back")
async def back_to_main_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню."""
    await callback.answer()
    
    from bot.handlers.start import main_menu_handler
    await main_menu_handler(callback.message, state)


def get_content_plan_list_keyboard(plans):
    """Создать клавиатуру со списком планов."""
    buttons = []
    
    for plan in plans:
        status_text = "✅" if plan.is_active else "⏸️"
        button_text = f"{status_text} {plan.plan_name}"
        callback_data = f"content_plan_manage_{plan.id}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    # Кнопка создания нового плана
    buttons.append([InlineKeyboardButton(text="➕ Создать новый план", callback_data="content_plan_create")])
    
    # Кнопка возврата
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню контент-планов", callback_data="content_plan")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="content_plan_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
