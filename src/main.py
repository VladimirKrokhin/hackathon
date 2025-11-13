import asyncio
import logging
import os

from aiogram import Bot, Dispatcher

from src.config import config
from src.bot.handlers import router
from src.services.card_generation import card_generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logger.info("🚀 Инициализация бота и подготовка окружения")

    await card_generator.init_browser()
    logger.info("✅ Браузер Playwright успешно инициализирован")

    for directory in ("templates", "temp"):
        os.makedirs(directory, exist_ok=True)
        logger.debug("📁 Директория %s готова", directory)

    required_templates = ("universal_card.html", "instagram_story.html", "telegram_post.html")
    for template in required_templates:
        template_path = os.path.join("templates", template)
        if not os.path.exists(template_path):
            logger.warning("⚠️ Шаблон %s не найден. Будет использован fallback-шаблон.", template)


async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    try:
        await card_generator.close_browser()
        logger.info("✅ Браузер Playwright успешно закрыт")
    except Exception as e:
        logger.error(f"❌ Ошибка при закрытии браузера: {e}")

    logger.info("👋 Завершение работы бота")


async def main():
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен в переменных окружения")
        return

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("🚀 Бот запускается...")
    logger.info("🔧 Режим отладки: %s", "ВКЛЮЧЕН" if config.DEBUG else "ВЫКЛЮЧЕН")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as exc:
        logger.exception("❌ Критическая ошибка: %s", exc)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
