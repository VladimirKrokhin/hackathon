from aiogram import Router
from aiogram.types import Message

from bot.keyboards.reply import get_goal_keyboard

fallback_router = Router(name="fallback")


@fallback_router.message()
async def fallback_handler(message: Message):
    await message.answer(
        "Я пока не понимаю эту команду. Нажмите /start или выберите цель из меню ниже, чтобы начать заново.",
        reply_markup=get_goal_keyboard(),
    )