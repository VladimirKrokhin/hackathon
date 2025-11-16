from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards.inline import get_goal_keyboard

fallback_router = Router(name="fallback")


@fallback_router.message()
async def fallback_handler(message: Message):
    await message.answer(
        "Я пока не понимаю эту команду. Нажмите или отправьте сообщение /start, чтобы начать взаимодействие с ботом.",
        reply_markup=ReplyKeyboardRemove(),
    )
