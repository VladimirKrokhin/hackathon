"""
Точка входа приложения
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from bootstrap import bootstrap
from bot import bot, dispatcher
from config import config

# Конфигурация логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def run_bot(bot: Bot, dispatcher: Dispatcher):
    await bootstrap(bot, dispatcher)

    logger.info("Запускаю обработку сообщений...")
    logger.info(f"Debug-режим: {'ВКЛЮЧЕН' if config.DEBUG else 'ВЫКЛЮЧЕН'}")

    try:
        await dispatcher.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен по прерыванию ввода.")
    except Exception as exc:
        logger.exception(f"Получена критическая ошибка: {exc}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":


    logger.info("Запускаю бота...")
    try:
        asyncio.run(run_bot(bot, dispatcher))
    except Exception as e:
        logger.exception(f"Ошибка при попытке запуска: {e}")
        raise
