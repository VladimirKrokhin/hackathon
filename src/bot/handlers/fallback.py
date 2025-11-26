from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove


fallback_router = Router(name="fallback")


@fallback_router.message()
async def fallback_handler(message: Message):
    await message.answer(
        ("Я пока не понимаю что вы хотите выполнить.\n\n"
        "Нажмите или отправьте сообщение /start, чтобы начать взаимодействие с ботом."),
        reply_markup=ReplyKeyboardRemove(),
    )
