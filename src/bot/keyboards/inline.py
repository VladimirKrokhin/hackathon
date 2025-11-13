from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_post_generation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Создать ещё", callback_data="create_again")],
            [InlineKeyboardButton(text="💡 Советы по продвижению", callback_data="get_tips")],
            [InlineKeyboardButton(text="📤 Экспортировать все", callback_data="export_all")],
        ]
    )