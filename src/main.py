"""
Точка входа приложения
"""

import asyncio
import logging
from bootstrap import bootstrap
from app import bot, dp

# Конфигурация логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Запускаю бота...")
    try:
        asyncio.run(bootstrap(bot, dp))
    except Exception as e:
        logger.exception(f"Ошибка при попытке запуска: {e}")
        raise
