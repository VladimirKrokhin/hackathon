from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton





def get_wizard_image_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления сгенерированным изображением."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="wizard_image_regenerate")],
            [InlineKeyboardButton(text="✏️ Изменить промпт", callback_data="wizard_image_edit_prompt")],
            [InlineKeyboardButton(text="🎨 Генерация карточки", callback_data="wizard_create_content")],
            [InlineKeyboardButton(text="⬅️ К тексту", callback_data="wizard_back_to_text")],
            [InlineKeyboardButton(text="↩️ К источнику", callback_data="wizard_back_to_image_source")]
        ]
    )


def get_wizard_final_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура финального подтверждения и завершения Wizard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎨 Создать контент", callback_data="wizard_create_content")],
            [InlineKeyboardButton(text="🔄 Изменить настройки", callback_data="wizard_modify_settings")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="wizard_back_to_image")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="wizard_back_to_main")]
        ]
    )


def get_wizard_back_navigation_keyboard() -> InlineKeyboardMarkup:
    """Универсальная клавиатура для навигации назад."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="wizard_back")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="wizard_main_menu")]
        ]
    )


def get_wizard_text_regenerate_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для уточнения причины перегенерации текста."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Случайные изменения", callback_data="wizard_regenerate_random")],
            [InlineKeyboardButton(text="✏️ Указать причину", callback_data="wizard_regenerate_custom")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="wizard_back_to_text_result")]
        ]
    )


def get_wizard_card_ready_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления готовыми к публикации материалами."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Перегенерировать карточки", callback_data="wizard_regenerate_card")],
            [InlineKeyboardButton(text="✏️ Изменить текст карточки", callback_data="wizard_edit_card_text")],
            [InlineKeyboardButton(text="📝 Написать промпт для карточки", callback_data="wizard_write_card_prompt")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="wizard_back_to_main")]
        ]
    )
