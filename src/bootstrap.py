import logging


from aiogram import Bot, Dispatcher, Router
from playwright.async_api import BrowserContext, async_playwright, Browser
from playwright.async_api import Playwright


from config import config
from bot.handlers import router
from infrastructure.prompt_builder import YandexGPTPromptBuilder
from infrastructure.response_processor import YandexGPTResponseProcessor
from infrastructure.card_generation import HTTPServerManager, PlaywrightCardGenerator, TEMPLATES_DIR
from services.content_generation import TextContentGenerationService
from services.card_generation import CardGenerationService
from infrastructure.gpt import YandexGPT
from infrastructure.database import init_database, get_db_session
from infrastructure.repositories.ngo_repository import NGORepository
from services.ngo_service import NGOService
from infrastructure.image_generation import create_fusion_brain_image_generator
from services.image_generation import ImageGenerationService



logger = logging.getLogger(__name__)




async def build_yandexgpt_content_generation_service() -> TextContentGenerationService:
    response_processor = YandexGPTResponseProcessor()
    gpt_client = YandexGPT()
    prompt_builder = YandexGPTPromptBuilder()

    service = TextContentGenerationService(
        prompt_builder=prompt_builder,
        gpt_client=gpt_client,
        response_processor=response_processor,
    )

    return service



async def build_playwright_card_generation_service(bot: Bot, dispatcher: Dispatcher) -> CardGenerationService:
    """Получение сервиса генерации карточек."""

    async def start_http_server(dispatcher: Dispatcher):
        http_server_manager = HTTPServerManager(TEMPLATES_DIR, port=8000)


        # Запуск HTTP-сервера для Playwright
        logger.info("Запуск HTTP-сервера для обслуживания шаблонов...")
        server_started = http_server_manager.start_in_thread()
        if server_started:
            logger.info("HTTP-сервер успешно запущен")
        else:
            logger.warning("HTTP-сервер не удалось запустить - возможны проблемы с генерацией карточек")

        return http_server_manager
        


    async def init_browser() -> tuple[Browser, Playwright]:
        logger.info("Инициализирую браузер Playwright...")
        playwright: Playwright = await async_playwright().start()
        browser: Browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        return (browser, playwright)

    async def close_browser(browser: Browser, playwright: Playwright) -> None:
        logger.info("Закрываю браузер Playwright...")

        browser_context: BrowserContext = dp.get("browser_context")
        if browser_context:
            await browser_context.close()
            
        await browser.close()
        await playwright.stop()

    async def stop_http_server(http_server_manager: HTTPServerManager):
        # Останавливаем HTTP-сервер
        logger.info("Остановка HTTP-сервера...")
        await http_server_manager.stop()

    async def on_shutdown(browser: Browser, playwright: Playwright, http_server_manager: HTTPServerManager):
        await close_browser(browser, playwright)
        await stop_http_server(http_server_manager)


    dp = dispatcher

    browser, playwright = await init_browser()
    http_server_manager = await start_http_server(dp)

    

    dp["browser"]: Browser = browser
    dp["playwright"]: Playwright = playwright
    dp["http_server_manager"]: HTTPServerManager = http_server_manager



    dp["on_shutdown"] = lambda: on_shutdown(browser, playwright, http_server_manager)
    

    card_generator = PlaywrightCardGenerator(browser=browser)
    service = CardGenerationService(card_generator=card_generator)
    return service



_create_content_generation_service: TextContentGenerationService = build_yandexgpt_content_generation_service
_create_card_generation_service: CardGenerationService = build_playwright_card_generation_service


async def build_services(bot: Bot, dispatcher: Dispatcher):
    dp = dispatcher

    dp["text_content_generation_service"]: TextContentGenerationService = await _create_content_generation_service()
    dp["card_generation_service"]: CardGenerationService = await _create_card_generation_service(bot, dp) 
    
    # Инициализируем сервис генерации изображений
    try:
        image_generator = create_fusion_brain_image_generator()
        image_generation_service = ImageGenerationService(image_generator=image_generator)
        dp["image_generation_service"] = image_generation_service
        logger.info("Сервис генерации изображений успешно инициализирован")
    except Exception as e:
        logger.warning(f"Не удалось инициализировать сервис генерации изображений: {e}")
        dp["image_generation_service"] = None
    
    # Инициализируем сервис НКО
    init_database()  # Инициализируем базу данных
    
    # Создаем фабрику для получения сессий и сервиса НКО
    def get_ngo_service():
        session = get_db_session()
        ngo_repository = NGORepository(session)
        return NGOService(ngo_repository)
    
    dp["get_ngo_service"] = get_ngo_service
    # Для обратной совместимости создаем один экземпляр
    dp["ngo_service"] = get_ngo_service()



async def on_startup(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot, ...], router: Router):
    """Действия при запуске бота."""
    logger.info("Инициализация бота и подготовка окружения")

    await build_services(bot, dispatcher)




async def on_shutdown(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot, ...], router: Router):
    """Действия при остановке бота."""
    logger.info("Завершение работы бота")

    dp = dispatcher


    on_shutdown = dp.get("on_shutdown")

    if on_shutdown:
        await on_shutdown()



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
