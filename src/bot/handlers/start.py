import logging

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.states import ContentGeneration
from bot.keyboards.reply import get_goal_keyboard

logger = logging.getLogger(__name__)

start_router = Router(name="start")


@start_router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """Точка входа в сценарий генерации контента."""
    await state.clear()
    await message.answer(
        "👋 Привет! Я — ContentHelper, ваш AI-ассистент для создания контента в НКО.\n\n"
        "Я помогу вам подготовить профессиональные посты и карточки для соцсетей за пару минут.\n\n"
        "Какова основная цель вашего поста?",
        reply_markup=get_goal_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_goal)


@start_router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Команда для сброса текущего сценария."""
    await state.clear()
    await message.answer(
        "❎ Текущий сценарий сброшен. Начнём заново!\n\n"
        "Выберите цель поста:",
        reply_markup=get_goal_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_goal)