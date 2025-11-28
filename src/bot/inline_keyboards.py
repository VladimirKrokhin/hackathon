from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton







def get_wizard_back_navigation_keyboard() -> InlineKeyboardMarkup:
    """Универсальная клавиатура для навигации назад."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="wizard_back")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="wizard_main_menu")]
        ]
    )


