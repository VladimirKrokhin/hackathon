from aiogram.fsm.state import State, StatesGroup


class ContentGeneration(StatesGroup):
    # Режимы генерации
    waiting_for_generation_mode = State()
    waiting_for_ngo_info_choice = State()
    
    # Структурированная форма (новые вопросы)
    waiting_for_event_type = State()
    waiting_for_event_date = State()
    waiting_for_event_place = State()
    waiting_for_event_audience = State()
    waiting_for_event_details = State()
    waiting_for_narrative_style = State()
    waiting_for_platform = State()
    
    # Свободная форма
    waiting_for_user_description = State()
    waiting_for_free_style = State()
    
    # Общие состояния
    waiting_for_confirmation = State()
    waiting_for_refactoring_text = State()


class ContentPlan(StatesGroup):
    waiting_for_period = State()
    waiting_for_custom_period = State()
    waiting_for_frequency = State()
    waiting_for_custom_frequency = State()
    waiting_for_themes = State()
    waiting_for_details = State()


class NGOInfo(StatesGroup):
    waiting_for_ngo_name = State()
    waiting_for_ngo_description = State()
    waiting_for_ngo_activities = State()
    waiting_for_ngo_contact = State()
    waiting_for_ngo_confirmation = State()
