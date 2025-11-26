from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton




def get_navigation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура навигации."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip")],
            [InlineKeyboardButton(text="✅ Готово", callback_data="done")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )




# ===== НОВЫЕ КЛАВИАТУРЫ ДЛЯ WIZARD =====




def get_wizard_text_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления сгенерированным текстом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="wizard_text_regenerate")],
            [InlineKeyboardButton(text="✏️ Исправить текст", callback_data="wizard_text_edit")],
            [InlineKeyboardButton(text="⚙️ Изменить параметры", callback_data="wizard_text_change_fields")],
            [InlineKeyboardButton(text="🎨 Генерация карточки", callback_data="wizard_to_image")],
            [InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="wizard_back_to_setup")]
        ]
    )


def get_wizard_field_select_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для изменения в структурированной форме."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Тип события", callback_data="wizard_edit_event_type")],
            [InlineKeyboardButton(text="📅 Дата события", callback_data="wizard_edit_event_date")],
            [InlineKeyboardButton(text="📍 Место события", callback_data="wizard_edit_event_place")],
            [InlineKeyboardButton(text="👥 Аудитория", callback_data="wizard_edit_event_audience")],
            [InlineKeyboardButton(text="📝 Детали события", callback_data="wizard_edit_event_details")],
            [InlineKeyboardButton(text="🎨 Стиль повествования", callback_data="wizard_edit_narrative_style")],
            [InlineKeyboardButton(text="📱 Платформа", callback_data="wizard_edit_platform")],
            [InlineKeyboardButton(text="✅ Сохранить и вернуться", callback_data="wizard_back_to_text_result")],
            [InlineKeyboardButton(text="⬅️ Назад к тексту", callback_data="wizard_back_to_text_result")]
        ]
    )



def get_wizard_image_prompt_preview_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для предпросмотра и управления промптом изображения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Перегенерировать промпт", callback_data="wizard_prompt_regenerate")],
            [InlineKeyboardButton(text="✏️ Изменить промпт", callback_data="wizard_prompt_edit")],
            [InlineKeyboardButton(text="✅ Сгенерировать изображение", callback_data="wizard_generate_image")],
            [InlineKeyboardButton(text="⬅️ К источнику изображения", callback_data="wizard_back_to_image_source")]
        ]
    )


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
