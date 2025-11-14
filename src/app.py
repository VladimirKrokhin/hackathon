from aiogram import Bot, Dispatcher

from config import config


bot = Bot(token=config.BOT_TOKEN)

dp = Dispatcher()