import asyncio
import logging
import os

from aiogram import Bot, Dispatcher

from config import config
from bot.handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def create_directories():
    for directory in ("templates", "temp"):
        os.makedirs(directory, exist_ok=True)
        logger.debug("Директория %s готова", directory)

async def check_templates():
    required_templates = ("universal_card.html", "telegram_post.html")
    for template in required_templates:
        template_path = os.path.join("templates", template)
        if not os.path.exists(template_path):
            logger.warning("Шаблон %s не найден. Будет использован fallback-шаблон.", template)


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logger.info("Инициализация бота и подготовка окружения")




async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    logger.info("Завершение работы бота")


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в переменных окружения")
        return

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Бот запускается...")
    logger.info(f"Режим отладки: {'ВКЛЮЧЕН' if config.DEBUG else 'ВЫКЛЮЧЕН'}")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as exc:
        logger.exception(f"Критическая ошибка: {exc}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
