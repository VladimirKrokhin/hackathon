import logging

from aiogram import Bot, Dispatcher

from config import config

logger = logging.getLogger(__name__)

if not config.BOT_TOKEN:
    logger.error("BOT_TOKEN не предоставлен в переменных окружения")
    raise ValueError("BOT_TOKEN не предоставлен в переменных окружения")

bot = Bot(token=config.BOT_TOKEN)
dispatcher = Dispatcher()