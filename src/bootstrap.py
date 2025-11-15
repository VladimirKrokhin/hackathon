import logging
from types import CoroutineType

from aiogram import Bot, Dispatcher, Router
from playwright.async_api import async_playwright, Browser

from config import config
from bot.handlers import router
from infrastructure.prompt_builder import YandexGPTPromptBuilder
from infrastructure.response_processor import YandexGPTResponseProcessor
from infrastructure.card_generation import PlaywrightCardGenerator
from services.content_generation import ContentGenerationService
from services.card_generation import CardGenerationService
from infrastructure.gpt import YandexGPT


logger = logging.getLogger(__name__)


async def init_browser() -> tuple[Browser, CoroutineType]:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )
    return (browser, playwright)

async def close_browser(browser: Browser, playwright: CoroutineType) -> None:
    await browser.close()
    await playwright.stop()


def build_yandexgpt_content_generation_service() -> ContentGenerationService:
    response_processor = YandexGPTResponseProcessor()
    gpt_client = YandexGPT()
    prompt_builder = YandexGPTPromptBuilder()

    service = ContentGenerationService(
        prompt_builder=prompt_builder,
        gpt_client=gpt_client,
        response_processor=response_processor,
    )

    return service



def build_playwright_card_generation_service(bot: Bot, dispatcher: Dispatcher) -> CardGenerationService:
    """Получение сервиса генерации карточек."""
    dp = dispatcher
    browser = dp["browser"]

    if browser is None:
        raise ValueError("Не инициализирован браузер!")

    card_generator = PlaywrightCardGenerator(browser=browser)
    service = CardGenerationService(card_generator=card_generator)
    return service




get_content_generation_service = build_yandexgpt_content_generation_service
get_card_generation_service = build_playwright_card_generation_service



async def on_startup(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot, ...], router: Router):
    """Действия при запуске бота."""
    logger.info("Инициализация бота и подготовка окружения")

    dp = dispatcher

    browser, playwright = await init_browser()
    
    dp["browser"] = browser
    dp["playwright"] = playwright

    dp["content_generation_service"] = get_content_generation_service()
    dp["card_generation_service"] = get_card_generation_service(bot, dp) 


async def on_shutdown(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot, ...], router: Router):
    """Действия при остановке бота."""
    logger.info("Завершение работы бота")

    dp = dispatcher

    browser = dp["browser"]
    playwright = dp["playwright"]

    await close_browser(browser, playwright)



async def bootstrap(bot: Bot, dispatcher: Dispatcher):
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в переменных окружения")
        raise ValueError

    dp = dispatcher

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
        
