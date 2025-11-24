"""
Состояния бота для управления потоком беседы и пользовательского взаимодействия.
"""

from aiogram.fsm.state import State, StatesGroup


class ContentGeneration(StatesGroup):
    """
    Состояния для процесса генерации контента (текста, картинок и карточек).
    """
    
    # Режим генерации
    waiting_for_generation_mode = State()
    waiting_for_ngo_info_choice = State()
    waiting_for_goal = State()

    # Структурированная форма
    waiting_for_event_type = State()
    waiting_for_event_date = State()
    waiting_for_event_place = State()
    waiting_for_event_audience = State()
    waiting_for_event_details = State()
    waiting_for_narrative_style = State()
    waiting_for_platform = State()

    # Выбор источника изображения
    waiting_for_image_source = State()
    waiting_for_image_prompt = State()
    waiting_for_user_image = State()

    # Свободная форма - выбор источника изображения
    waiting_for_free_image_source = State()
    waiting_for_free_image_prompt = State()
    waiting_for_free_user_image = State()

    # Свободная форма - характеристика контента
    waiting_for_user_description = State()
    waiting_for_free_style = State()
    waiting_for_free_platform = State()

    # Основные состояния
    waiting_for_confirmation = State()
    waiting_for_card_photo_choice = State()
    waiting_for_card_photo_prompt = State()
    waiting_for_card_user_photo = State()
    waiting_for_refactoring_text = State()

    # Генерация картинок
    waiting_for_image_description = State()
    waiting_for_image_style = State()
    waiting_for_image_size = State()


class ContentWizard(StatesGroup):
    """
    Состояния для Мастера генерации контента.

    Реализует пошагового мастера для пошаговой генерации контента. 
    """
    
    # Шаг 1: Базовая настройка
    waiting_for_wizard_start = State()
    waiting_for_wizard_mode = State()  # Структурированная/Свободная форма
    waiting_for_wizard_ngo = State()   # Использовать информацию о НКО?

    # Шаг 2: Генерация текста (структурированная форма)
    waiting_for_wizard_text_setup = State()
    waiting_for_wizard_event_date = State()
    waiting_for_wizard_event_place = State()
    waiting_for_wizard_event_audience = State()
    waiting_for_wizard_event_details = State()
    waiting_for_wizard_event_style = State()
    waiting_for_wizard_event_platform = State()

    # Шаг 3: Генерация и редактирование текста
    waiting_for_wizard_text_result = State()
    waiting_for_wizard_text_edit = State()     # Редактирование текста
    waiting_for_wizard_text_regenerate = State()  # Перегенерация

    # Шаг 4: Выбор поля для изменения (структирурованная форма)
    waiting_for_wizard_field_select = State()
    waiting_for_wizard_event_type_edit = State()
    waiting_for_wizard_event_date_edit = State()
    waiting_for_wizard_event_place_edit = State()
    waiting_for_wizard_event_audience_edit = State()
    waiting_for_wizard_event_details_edit = State()
    waiting_for_wizard_narrative_style_edit = State()
    waiting_for_wizard_platform_edit = State()

    # Шаг 5: Обработка изображений
    waiting_for_wizard_image_source = State()
    waiting_for_wizard_image_prompt = State()
    waiting_for_wizard_image_prompt_edit = State()  # Промпт для ИИ
    waiting_for_wizard_image_user_upload = State()  # Загрузка пользовательского изображения
    waiting_for_wizard_image_result = State()

    # Шаг 6: Подтверждение
    waiting_for_wizard_final_confirm = State()

    # Шаг 7: Редактирование текста карточки
    waiting_for_wizard_card_text_edit = State()
    waiting_for_wizard_card_prompt = State()


class ContentPlan(StatesGroup):
    """
    Состояния для процесса создания контент-плана.
    """
    
    waiting_for_period = State()
    waiting_for_custom_period = State()
    waiting_for_frequency = State()
    waiting_for_custom_frequency = State()
    waiting_for_themes = State()
    waiting_for_details = State()


class EditText(StatesGroup):
    """
    Состояния для редактирования текста.
    """
    
    waiting_for_text = State()
    waiting_for_details = State()


class NGOInfo(StatesGroup):
    """
    Состояния для сбора информации о НКО.
    """
    
    waiting_for_ngo_name = State()
    waiting_for_ngo_description = State()
    waiting_for_ngo_activities = State()
    waiting_for_ngo_contact = State()
    waiting_for_ngo_confirmation = State()


class ImageGeneration(StatesGroup):
    """
    Состояния для генерации изображения.
    """
    
    waiting_for_prompt = State()
    waiting_for_size = State()
