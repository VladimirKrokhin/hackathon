from aiogram.fsm.state import State, StatesGroup


class ContentGeneration(StatesGroup):
    waiting_for_goal = State()
    waiting_for_audience = State()
    waiting_for_platform = State()
    waiting_for_format = State()
    waiting_for_has_event = State()
    waiting_for_event_details = State()
    waiting_for_volume = State()
    waiting_for_user_text = State()
    waiting_for_confirmation = State()
    waiting_for_refactoring_text = State()