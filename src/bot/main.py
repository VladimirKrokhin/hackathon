import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from config import config
from bot.handlers import router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    """Действия при старте бота"""
    try:
        pass
    except Exception as e:
        logger.error(f"Ошибка при инициализации: {e}")

async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    try:
        pass
    except Exception as e:
        logger.error(f"Ошибка при остановке бота: {e}")

async def main():
    """Основная функция запуска бота"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в переменных окружения")
        return
    
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Подключаем роутеры
    dp.include_router(router)
    
    # Регистрируем обработчики событий
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logger.info("Бот запускается...")
    logger.info(f"🔧 Режим отладки: {'ВКЛЮЧЕН' if config.DEBUG else 'ВЫКЛЮЧЕН'}")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        logger.error(f"Ошибка выполнения: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")