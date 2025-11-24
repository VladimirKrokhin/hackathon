"""
Конфигурация и инициализация приложения

Этот модуль содержит ключевые объекты приложения:
- экземпляр бота
- экземпляр диспетчера
для обработки сообщений и команд Telegram
"""

from aiogram import Bot, Dispatcher
from config import config

bot = Bot(token=config.BOT_TOKEN)

dp = Dispatcher()
