import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.handlers.start import start_handler

callbacks_router = Router(name="callbacks")
logger = logging.getLogger(__name__)


@callbacks_router.callback_query(F.data == "create_again")
async def create_again_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


@callbacks_router.callback_query(F.data == "export_all")
async def export_all_handler(callback: CallbackQuery):
    await callback.answer(
        "📦 Функция экспорта всех материалов будет доступна в продакшн-версии.",
        show_alert=True,
    )


@callbacks_router.callback_query(F.data == "get_tips")
async def get_tips_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    platform = data.get("platform", "")
    audience = ", ".join(data.get("audience", [])) or "не указана"
    goal = data.get("goal", "вашей задачи")

    tips_map = {
        "📱 ВКонтакте (для молодежи)": (
            "💡 Советы для ВКонтакте:\n\n"
            "• Публикуйте в 18:00–21:00, когда аудитория наиболее активна\n"
            "• Используйте 3–5 релевантных хештегов\n"
            "• Добавляйте эмодзи в начале каждого абзаца\n"
            "• Публикуйте 3–4 раза в неделю для поддержания интереса\n"
            "• Отвечайте на комментарии в течение 1–2 часов"
        ),
        "💬 Telegram (для взрослых/бизнеса)": (
            "💡 Советы для Telegram:\n\n"
            "• Публикуйте в рабочие дни с 10:00 до 16:00\n"
            "• Используйте форматирование (**жирный**, _курсив_)\n"
            "• Добавляйте разделители --- между секциями\n"
            "• Публикуйте 1–2 раза в неделю, чтобы не спамить\n"
            "• Используйте кнопки для призывов к действию"
        ),
    }

    tips_text = tips_map.get(
        platform,
        "💡 Общие советы по продвижению:\n\n"
        "• Публикуйте регулярно, чтобы аудитория не забывала о вас\n"
        "• Комбинируйте информационный и эмоциональный контент\n"
        "• Задавайте вопросы в постах для повышения вовлечённости\n"
        "• Анализируйте статистику и корректируйте стратегию\n"
        "• Сотрудничайте с другими НКО для взаимного продвижения",
    )

    await callback.message.answer(
        f"Цель: {goal}\nАудитория: {audience}\nПлатформа: {platform or '—'}\n\n{tips_text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Создать ещё", callback_data="create_again")],
            ]
        ),
    )