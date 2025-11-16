from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_post_generation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Создать ещё", callback_data="create_again")],
            [InlineKeyboardButton(text="💡 Советы по продвижению", callback_data="get_tips")],
            [InlineKeyboardButton(text="📤 Экспортировать все", callback_data="export_all")],
            [InlineKeyboardButton(text="✏️ Переработать текст", callback_data="refactor_content")]
        ]
    )


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с inline кнопками."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создание контента", callback_data="create_content")],
            [InlineKeyboardButton(text="📅 Контент-план", callback_data="content_plan")],
            [InlineKeyboardButton(text="✏️ Редактировать текст", callback_data="edit_text")],
            [InlineKeyboardButton(text="🎨 Генерация картинок", callback_data="generate_images")],
            [InlineKeyboardButton(text="📋 Информация о НКО", callback_data="ngo_info")]
        ]
    )


def get_content_creation_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню создания контента."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать контент", callback_data="create_content_form")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )


def get_content_form_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню выбора формы создания контента."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Структурированная форма", callback_data="structured_content")],
            [InlineKeyboardButton(text="💭 Свободная форма", callback_data="free_form_content")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_content_menu")]
        ]
    )


def get_ngo_info_menu_keyboard(has_ngo_data: bool = False) -> InlineKeyboardMarkup:
    """Меню информации о НКО с условными кнопками."""
    buttons = []
    
    if has_ngo_data:
        buttons.append([InlineKeyboardButton(text="📋 Посмотреть мою НКО", callback_data="view_ngo")])
        buttons.append([InlineKeyboardButton(text="🔄 Обновить данные НКО", callback_data="update_ngo")])
    
    buttons.append([InlineKeyboardButton(text="🏢 Заполнить информацию об НКО", callback_data="fill_ngo")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_ngo_data_missing_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при отсутствии данных о НКО."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="yes_fill_ngo"), 
             InlineKeyboardButton(text="❌ Нет", callback_data="no_fill_ngo")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )


def get_content_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа создания контента."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Структурированная форма", callback_data="structured_content")],
            [InlineKeyboardButton(text="💭 Свободная форма", callback_data="free_form_content")],
            [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main")]
        ]
    )


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с вариантами Да/Нет."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="yes"), 
             InlineKeyboardButton(text="❌ Нет", callback_data="no")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )


def get_navigation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура навигации."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip")],
            [InlineKeyboardButton(text="✅ Готово", callback_data="done")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


# Новые клавиатуры для миграции с ReplyKeyboard

def get_generation_mode_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора режима генерации контента."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Структурированная форма (пошаговый опрос)", callback_data="generation_mode_structured")],
            [InlineKeyboardButton(text="💭 Свободная форма (самостоятельное описание)", callback_data="generation_mode_free")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )


def get_narrative_style_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора стиля повествования."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Разговорный стиль", callback_data="narrative_conversational")],
            [InlineKeyboardButton(text="📋 Официально-деловой стиль", callback_data="narrative_official")],
            [InlineKeyboardButton(text="🎨 Художественный стиль", callback_data="narrative_artistic")],
            [InlineKeyboardButton(text="🌟 Позитивный/мотивирующий стиль", callback_data="narrative_motivational")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
        ]
    )


def get_goal_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цели поста."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Привлечь волонтеров", callback_data="goal_volunteers")],
            [InlineKeyboardButton(text="💰 Найти спонсоров/доноров", callback_data="goal_sponsors")],
            [InlineKeyboardButton(text="📢 Рассказать о мероприятии", callback_data="goal_event")],
            [InlineKeyboardButton(text="❤️ Повысить осведомленность о проблеме", callback_data="goal_awareness")],
            [InlineKeyboardButton(text="🤝 Укрепить отношения со сторонниками", callback_data="goal_relationships")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
        ]
    )


def get_audience_keyboard(selected: list = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора аудитории (множественный выбор)."""
    buttons = []
    
    # Кнопки выбора аудитории
    audience_options = [
        ("👨‍🎓 Молодежь (14-25 лет)", "audience_youth"),
        ("👨‍👩‍👧‍👦 Семьи с детьми", "audience_families"),
        ("💼 Работающие взрослые (25-45 лет)", "audience_adults"),
        ("👴 Люди старшего возраста (45+)", "audience_seniors"),
        ("🏢 Бизнес/организации", "audience_business"),
    ]
    
    for text, callback in audience_options:
        if selected and callback.replace("audience_", "") in [s.replace("audience_", "") for s in selected]:
            text = f"✅ {text}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])
    
    # Кнопки действий
    buttons.extend([
        [InlineKeyboardButton(text="✅ Готово", callback_data="audience_done")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора платформы."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 ВКонтакте (для молодежи)", callback_data="platform_vk")],
            [InlineKeyboardButton(text="💬 Telegram (для взрослых/бизнеса)", callback_data="platform_telegram")],
            [InlineKeyboardButton(text="📸 Instagram (визуальный контент)", callback_data="platform_instagram")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
        ]
    )


def get_image_source_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора источника изображения для карточки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Сгенерировать ИИ", callback_data="image_source_ai")],
            [InlineKeyboardButton(text="📎 Загрузить своё", callback_data="image_source_upload")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_platform")]
        ]
    )


def get_format_keyboard(selected: list = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора формата поста (множественный выбор)."""
    buttons = []
    
    # Кнопки выбора формата
    format_options = [
        ("📝 Информационный пост (70% контента)", "format_informational"),
        ("🎭 Развлекательный/эмоциональный пост (20%)", "format_entertainment"),
        ("💬 Пост для вовлечения аудитории (10%)", "format_engagement"),
        ("📅 Напоминание о мероприятии", "format_event_reminder"),
    ]
    
    for text, callback in format_options:
        if selected and callback.replace("format_", "") in [s.replace("format_", "") for s in selected]:
            text = f"✅ {text}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])
    
    # Кнопки действий
    buttons.extend([
        [InlineKeyboardButton(text="✅ Готово", callback_data="format_done")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_volume_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора объема контента."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Короткий пост (1-3 предложения + карточка)", callback_data="volume_short")],
            [InlineKeyboardButton(text="📝 Средний пост (3-5 предложений + 2-3 карточки)", callback_data="volume_medium")],
            [InlineKeyboardButton(text="📖 Развернутый пост (5+ предложений + 4-5 карточек)", callback_data="volume_long")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
        ]
    )


def get_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода для контент-плана."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="3 дня", callback_data="period_3days")],
            [InlineKeyboardButton(text="Неделя", callback_data="period_week")],
            [InlineKeyboardButton(text="Месяц", callback_data="period_month")],
            [InlineKeyboardButton(text="🖊️ Свой вариант", callback_data="period_custom")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
        ]
    )


def get_frequency_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора частоты публикаций."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="каждый день", callback_data="frequency_daily")],
            [InlineKeyboardButton(text="раз в два дня", callback_data="frequency_every_two_days")],
            [InlineKeyboardButton(text="🖊️ Свой вариант", callback_data="frequency_custom")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
        ]
    )


def get_skip_keyboard(label: str = "Пропустить") -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой пропуска."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"⏩ {label}", callback_data="skip_step")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
        ]
    )


def get_ngo_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню НКО."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏢 Заполнить информацию об НКО", callback_data="ngo_fill_info")],
            [InlineKeyboardButton(text="✨ Создать контент без НКО", callback_data="create_content_without_ngo")],
            [InlineKeyboardButton(text="📝 Создать контент (структурированная форма)", callback_data="ngo_structured_content")],
            [InlineKeyboardButton(text="💭 Создать контент (свободная форма)", callback_data="ngo_free_content")],
            [InlineKeyboardButton(text="📋 Посмотреть мою НКО", callback_data="ngo_view")],
            [InlineKeyboardButton(text="🔄 Обновить данные НКО", callback_data="ngo_update")],
            [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main")]
        ]
    )


def get_ngo_navigation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура навигации для процесса НКО."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="ngo_cancel")],
            [InlineKeyboardButton(text="⏩ Пропустить", callback_data="ngo_skip")],
            [InlineKeyboardButton(text="✅ Готово", callback_data="ngo_done")]
        ]
    )


def get_image_generation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню генерации изображений."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Описать изображение", callback_data="describe_image")],
            [InlineKeyboardButton(text="🎭 Из созданного контента", callback_data="image_from_content")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )


def get_image_style_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора стиля изображения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎨 Реалистичный", callback_data="image_style_realistic")],
            [InlineKeyboardButton(text="🌈 Иллюстрация", callback_data="image_style_illustration")],
            [InlineKeyboardButton(text="⚪ Минимум", callback_data="image_style_minimal")],
            [InlineKeyboardButton(text="🔷 Абстрактный", callback_data="image_style_abstract")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_image_menu")]
        ]
    )


def get_image_size_inline_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора размера изображения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Квадрат (1024×1024)", callback_data="image_size_1024x1024")],
            [InlineKeyboardButton(text="📺 Горизонтал (1200×630)", callback_data="image_size_1200x630")],
            [InlineKeyboardButton(text="📱 Вертикал (630×1200)", callback_data="image_size_630x1200")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_style_selection")]
        ]
    )
