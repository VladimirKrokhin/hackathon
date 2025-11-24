"""
Модуль скрипта начальной инициализации для приложения.

Этот модуль управляет инициализацией всех необходимых сервисов и компонентов:
- Сервис генерации текстов (YandexGPT)
- Сервис генерации карточек (PIL и Playwright)
- Инициализация базы данных и сервиса управления НКО
- Сервисы контент-планов и уведомлений

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
from service_bus import service_bus
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
from infrastructure.repositories.content_plan_repository import ContentPlanRepository
from services.content_plan_service import ContentPlanService
from services.notification_service import NotificationService
from scheduler.content_plan_scheduler import ContentPlanScheduler

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

    async def start_http_server() -> HTTPServerManager:
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
        
    async def close_browser_and_stop_server(
        browser: Browser, 
        playwright: Playwright, 
        http_server_manager: HTTPServerManager,
        dispatcher: Dispatcher
    ):
        """Закрывает браузер и останавливает HTTP-сервер."""
        logger.info("Закрываю браузер Playwright...")
        browser_context: BrowserContext = dispatcher.get("browser_context")
        if browser_context:
            await browser_context.close()
            
        await browser.close()
        await playwright.stop()

        logger.info("Останавливаю HTTP-сервер...")
        await http_server_manager.stop()

    # Инициализация компонентов
    browser, playwright = await init_browser()
    http_server_manager = await start_http_server()

    # Хранит зависимости в диспетчере
    dispatcher["browser"]: Browser = browser
    dispatcher["playwright"]: Playwright = playwright
    dispatcher["http_server_manager"]: HTTPServerManager = http_server_manager

    # Регистрация shutdown функции в ServiceBus
    shutdown_func = lambda: close_browser_and_stop_server(
        browser, playwright, http_server_manager, dispatcher
    )
    service_bus.register_shutdown(shutdown_func)
    
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


async def build_content_plan_services(bot: Bot) -> tuple[ContentPlanService, NotificationService, ContentPlanScheduler, ContentPlanRepository]:
    """
    Инициализирует сервисы для работы с контент-планами.
    
    Args:
        bot: Экземпляр бота Telegram
        
    Returns:
        tuple: (ContentPlanService, NotificationService, ContentPlanScheduler, ContentPlanRepository)
    """
    logger.info("Инициализация сервисов контент-плана...")
    
    # Инициализируем базу данных и репозиторий с сессией
    init_database()  # Инициализирует соединение с базой данных
    session = get_db_session()
    content_plan_repository = ContentPlanRepository(session)
    
    # Создаем сервисы
    content_plan_service = ContentPlanService(content_plan_repository)
    notification_service = NotificationService(bot, content_plan_repository)
    scheduler = ContentPlanScheduler(notification_service)
    
    # Регистрация функций запуска и остановки планировщика в ServiceBus
    def start_scheduler():
        """Запускает планировщик."""
        scheduler.start()
        logger.info("Планировщик уведомлений контент-плана запущен")

    def stop_scheduler():
        """Останавливает планировщик."""
        scheduler.stop()
        logger.info("Планировщик уведомлений остановлен")

    service_bus.register_startup(start_scheduler)
    service_bus.register_shutdown(stop_scheduler)
    
    logger.info("Сервисы контент-плана успешно инициализированы")
    return content_plan_service, notification_service, scheduler, content_plan_repository


def build_ngo_service() -> NGOService:
    """
    Инициализирует и конфигурирует сервис управления НКО.
    
    Returns:
        NGOService: Сервис управления НКО
        
    Raises:
        Exception: Если инициализация падает
    """    
    # Инициализирует базу данных и сервис НКО
    init_database()  # Инициализирует соединеие с базой данных
    session = get_db_session()
    ngo_repository = NGORepository(session)
    return NGOService(ngo_repository)

# Конфигурация фабричных методов
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
    
    # Инициализируем сервисы контент-плана
    content_plan_service, notification_service, scheduler, _ = await build_content_plan_services(bot)
    dp["content_plan_service"] = content_plan_service
    dp["notification_service"] = notification_service
    dp["content_plan_scheduler"] = scheduler

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
    
    # Выполняем все зарегистрированные startup функции через ServiceBus
    await service_bus.execute_startup()


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

    # Выполняем все зарегистрированные shutdown функции через ServiceBus
    await service_bus.execute_shutdown()


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
