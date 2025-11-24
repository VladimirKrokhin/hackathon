"""
Модуль скрипта начальной инициализации для приложения.

Этот модуль управляет инициализацией всех необходимых сервисов и компонентов:
- Сервис генерации текстов (YandexGPT)
- Сервис генерации карточек (PIL и Playwright)
- Инициализация базы данных и сервиса управления НКО

Также модуль предоставляет фабричные функции для создания сущностей сервисов и
процедуры обработки запуска и остановки приложения.
"""

import logging
from typing import Tuple

from aiogram import Bot, Dispatcher, Router
from playwright.async_api import BrowserContext, async_playwright, Browser
from playwright.async_api import Playwright

from config import config
from bot.handlers import router
from infrastructure.prompt_builder import YandexGPTPromptBuilder
from infrastructure.response_processor import YandexGPTResponseProcessor
from infrastructure.card_generation import (
    HTTPServerManager, 
    PlaywrightCardGenerator, 
    PILCardGenerator, 
    TEMPLATES_DIR
)
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
    """
    Инициализирует и конфигурирует сервис генерации текста YandexGPT.
    
    Returns:
        TextContentGenerationService: Сконфигурированный сервис для текстовой генерации
        
    Raises:
        Exception: Если инициализация падает
    """
    logger.info("Инициализирую сервис генерации текста YandexGPT...")
    
    response_processor = YandexGPTResponseProcessor()
    gpt_client = YandexGPT()
    prompt_builder = YandexGPTPromptBuilder()

    service = TextContentGenerationService(
        prompt_builder=prompt_builder,
        gpt_client=gpt_client,
        response_processor=response_processor,
    )

    logger.info("Сервис генерации текста YandexGPT успешно инициализирован")
    return service


async def build_playwright_card_generation_service(bot: Bot, dispatcher: Dispatcher) -> CardGenerationService:
    """
    Инициализирует и конфигурирует сервис генерации карточек на основе Playwright.

    Также поднимает HTTP сервер для выдачи файлов и инициализрует браузер.
    
    
    Args:
        bot: Экземпляр бота Telegram
        dispatcher: Диспетчер бота
        
    Returns:
        CardGenerationService: Сервис генерации карточей
        
    Raises:
        Exception: Если инициализация проваливается
    """
    logger.info("Инициализация сервиса генерации карточек Playwright...")

    async def start_http_server(dispatcher: Dispatcher):
        """Запускает HTTP-сервер для выдачи файлов."""
        http_server_manager = HTTPServerManager(TEMPLATES_DIR, port=8000)

        logger.info("Запускаю HTTP-сервер...")
        server_started = http_server_manager.start_in_thread()
        if server_started:
            logger.info("HTTP-сервер успешно запущен")
        else:
            logger.warning("Не удалось запустить HTTP-сервер")
            raise Exception("Не удалось запустить HTTP-сервер")

        return http_server_manager
        
    async def init_browser() -> tuple[Browser, Playwright]:
        """Инициализирует сущность браузера для Playwright."""
        ARGS = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]

        logger.info("Инициализирую браузер Playwright...")
        playwright: Playwright = await async_playwright().start()
        browser: Browser = await playwright.chromium.launch(
            headless=True,
            args=ARGS,
        )
        return (browser, playwright)

    async def close_browser(browser: Browser, playwright: Playwright) -> None:
        """Останавливает браузер Playwright и высвобождает ресурсы."""
        logger.info("Закрываю браузер Playwright...")

        browser_context: BrowserContext = dp.get("browser_context")
        if browser_context:
            await browser_context.close()
            
        await browser.close()
        await playwright.stop()

    async def stop_http_server(http_server_manager: HTTPServerManager):
        """Останавливает HTTP-сервер."""
        logger.info("Остановка HTTP-сервера...")
        await http_server_manager.stop()

    async def on_shutdown(browser: Browser, playwright: Playwright, http_server_manager: HTTPServerManager):
        """Остановка и освобождение ресурсов."""

        # TODO: переделай на шину
        await close_browser(browser, playwright)
        await stop_http_server(http_server_manager)

    dp = dispatcher

    browser, playwright = await init_browser()
    http_server_manager = await start_http_server(dp)

    # Хранит зависимости в диспетчере
    dp["browser"]: Browser = browser
    dp["playwright"]: Playwright = playwright
    dp["http_server_manager"]: HTTPServerManager = http_server_manager

    dp["on_shutdown"] = lambda: on_shutdown(browser, playwright, http_server_manager)
    
    card_generator = PlaywrightCardGenerator(browser=browser)
    service = CardGenerationService(card_generator=card_generator)

    logger.info("Сервис генерации карточек Playwright успешно инициализирован")
    return service


async def build_pil_card_generation_service(bot: Bot, dispatcher: Dispatcher) -> CardGenerationService:
    """
    Инициализирует и конфигурирует сервис генерации карточек на основе PIL.

    Args:
        bot: Сущность Telegram-бота
        dispatcher: Диспетчер бота
        
    Returns:
        CardGenerationService: Сервис генерации карточек
    """
    logger.info("Инициализирую сервис генерации PIL...")

    card_generator = PILCardGenerator()
    service = CardGenerationService(card_generator=card_generator)

    logger.info("Сервис генерации карточек PIL успешно инициализирован.")
    return service


async def build_fusion_brain_image_generation_service() -> ImageGenerationService:
    """
    Инициализирует и конфигурирует сервис генерации изображений FusionBrain.
    
    Returns:
        ImageGenerationService: Сервис генерации изображений
        
    Raises:
        Exception: Если инициализация падает
    """
    logger.info("Инициализация сервиса генерации изображений FusionBrain...")
    image_generator = create_fusion_brain_image_generator()
    image_generation_service = ImageGenerationService(image_generator=image_generator)
    logger.info("Сервис генерации изображений FusionBrain успешно инициализирован")
    return image_generation_service




def build_ngo_service() -> NGOService:
    """
    Инициализирует и конфигурирует сервис управления НКО.
    
    Returns:
        NGOService: Сервис управления НКО
        
    Raises:
        Exception: Если инициализация падает
    """    # Инициализирует базу данных и сервис НКО
    init_database()  # Инициализирует соединеие с базой данных
    session = get_db_session()
    ngo_repository = NGORepository(session)
    return NGOService(ngo_repository)

# Конфигурация фабричных методов
# TODO: перепиши на абстрактную фабрику - выдели отдельный класс
_create_content_generation_service: TextContentGenerationService = build_yandexgpt_content_generation_service
_create_card_generation_service: CardGenerationService = build_pil_card_generation_service
_create_image_generation_service: ImageGenerationService = build_fusion_brain_image_generation_service
_create_ngo_service: NGOService = build_ngo_service


async def build_services(bot: Bot, dispatcher: Dispatcher):
    """
    Инициализирует и настраивает все сервисы приложения.
    
    Args:
        bot: Сущность Telegram-бота
        dispatcher: Диспетчер
        
    Raises:
        Exception: Если любой из сервисов падает
    """
    logger.info("Собираю сервисы приложения...")
    dp = dispatcher

    # Инициализирует сервисы генерации изображений
    dp["text_content_generation_service"]: TextContentGenerationService = await _create_content_generation_service()
    dp["card_generation_service"]: CardGenerationService = await _create_card_generation_service(bot, dp) 
    dp["image_generation_service"]: ImageGenerationService = await _create_image_generation_service()
    

    
    dp["ngo_service"] = _create_ngo_service()

    logger.info("Сервисы приложения успешно собраны")


async def on_startup(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot, ...], router: Router):
    """
    Выполняет необходимые процедуры при инициализации приложения

    Args:
        bot: Сущность Telegram-бота
        dispatcher: Диспетчер
        bots: Кортеж сущностей ботов (обычно один бот)
        router: Основной router для обработки сообщений
    """
    logger.info("Инициализирую бота и подготавливаю окружение")
    await build_services(bot, dispatcher)


async def on_shutdown(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot, ...], router: Router):
    """
    Выполняет правильную процедуру остановки.
    
    Args:
        bot: Сущность Telegram-бота
        dispatcher: Диспетчер
        bots: Кортеж сущностей ботов (обычно один бот)
        router: Основной router для обработки сообщений
    """
    logger.info("Останавливаю бота")

    dp = dispatcher
    # TODO: перепиши на шину
    on_shutdown = dp.get("on_shutdown")

    if on_shutdown:
        await on_shutdown()


async def bootstrap(bot: Bot, dispatcher: Dispatcher):
    """
    Основная функция запуска приложения.

    Args:
        bot: Сущность Telegram-бота.
        dispatcher: Диспетчер
        
    Raises:
        ValueError:  BOT_TOKEN не предоставлен
        Exception: Остальные исключения
    """
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не предоставлен в переменных окружения")
        raise ValueError("BOT_TOKEN не предоставлен в переменных окружения")

    dp = dispatcher

    # Регистарция основного router
    dp.include_router(router)

    # Регистрация обработчиков событий жизненного цикла программы
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Запускаю обработку сообщений...")
    logger.info(f"Debug-режим: {'ВКЛЮЧЕН' if config.DEBUG else 'ВЫКЛЮЧЕН'}")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен по прерыванию ввода.")
    except Exception as exc:
        logger.exception(f"Получена критическая ошибка: {exc}")
        raise
    finally:
        await bot.session.close()
