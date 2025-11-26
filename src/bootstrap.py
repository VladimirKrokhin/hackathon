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

from aiogram import Bot, Dispatcher, Router

from config import config
from bot.handlers import router
from infrastructure.image_generation import FusionBrainImageGenerator, AbstractImageGenerator
from infrastructure.publication_notificator import AbstractNotificator, TelegramBotNotificator
from service_bus import service_bus

from infrastructure.prompt_builder import YandexGPTPromptBuilder, AbstractPromptBuilder
from infrastructure.response_processor import YandexGPTResponseProcessor, AbstractResponseProcessor
from infrastructure.card_generation import (
    PillowCardGenerator, BaseCardGenerator,
)
from infrastructure.gpt import YandexGPT, AbstractGPT
from infrastructure.repositories.sqlalchemy.database import init_database, get_db_session
from infrastructure.repositories.ngo_repository import SqlAlchemyNgoRepository, AbstractNGORepository
from infrastructure.repositories.content_plan_repository import SqlAlchemyContentPlanRepository, \
    AbstractContentPlanRepository
from services.ngo_service import NGOService

from services.text_generation import TextGenerationService
from services.card_generation import CardGenerationService
from services.image_generation import ImageGenerationService
from services.content_plan_service import ContentPlanService
from services.notification_service import NotificationService

from infrastructure.content_plan_scheduler import ContentPlanScheduler, start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


__all__ = ["bootstrap"]


async def build_and_bind_services(bot: Bot, dispatcher: Dispatcher):
    """
    Инициализирует и привязывает все сервисы приложения.
    
    Args:
        bot: Сущность Telegram-бота
        dispatcher: Диспетчер
    """
    logger.info("Собираю сервисы приложения...")

    sqlalchemy_db = init_database()
    session = get_db_session()

    response_processor: AbstractResponseProcessor = YandexGPTResponseProcessor()
    gpt_client: AbstractGPT = YandexGPT()
    prompt_builder: AbstractPromptBuilder = YandexGPTPromptBuilder()
    card_generator: BaseCardGenerator = PillowCardGenerator()
    content_plan_repository: AbstractContentPlanRepository = SqlAlchemyContentPlanRepository(session)



    if not config.FUSION_BRAIN_API_KEY or not config.FUSION_BRAIN_SECRET_KEY:
        raise ValueError(
            "FUSION_BRAIN_API_KEY и FUSION_BRAIN_SECRET_KEY должны быть установлены в .env файле"
        )

    image_generator: AbstractImageGenerator = FusionBrainImageGenerator(
        api_key=config.FUSION_BRAIN_API_KEY,
        secret_key=config.FUSION_BRAIN_SECRET_KEY,
        api_url=config.FUSION_BRAIN_API_URL,
        pipeline_id="",  # Будет получен динамически при первой генерации
        timeout=config.FUSION_BRAIN_TIMEOUT,
        poll_interval=config.FUSION_BRAIN_POLL_INTERVAL,
        max_poll_attempts=config.FUSION_BRAIN_MAX_POLL_ATTEMPTS,
    )

    tg_notificator: AbstractNotificator = TelegramBotNotificator(
        bot=bot,
    )

    ngo_repository: AbstractNGORepository = SqlAlchemyNgoRepository(session)

    # Инициализирует сервисы генерации изображений
    dispatcher["text_content_generation_service"]: TextGenerationService = TextGenerationService(
        prompt_builder=prompt_builder,
        gpt_client=gpt_client,
        response_processor=response_processor,
    )
    dispatcher["card_generation_service"]: CardGenerationService = CardGenerationService(
        card_generator=card_generator,
        prompt_builder=prompt_builder,
        gpt_client=gpt_client,
        response_processor=response_processor,
    )

    dispatcher["image_generation_service"]: ImageGenerationService = ImageGenerationService(
        image_generator=image_generator
    )

    dispatcher["ngo_service"] = NGOService(
        repository=ngo_repository,
    )
    
    dispatcher["content_plan_service"] = ContentPlanService(
        content_plan_repository=content_plan_repository,
        prompt_builder=prompt_builder,
        gpt_client=gpt_client,
        response_processor=response_processor,
    )
    notification_service = NotificationService(tg_notificator, content_plan_repository)
    dispatcher["notification_service"] = notification_service
    content_plan_scheduler: ContentPlanScheduler = ContentPlanScheduler(notification_service)


    dispatcher["content_plan_scheduler"] = content_plan_scheduler



    service_bus.register_startup(lambda: start_scheduler(scheduler=content_plan_scheduler))
    service_bus.register_shutdown(lambda: stop_scheduler(scheduler=content_plan_scheduler))

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
    Основная функция инициализации приложения.

    Args:
        bot: Бот
        dispatcher: Диспетчер
    """

    # Регистрация основного router
    dispatcher.include_router(router)
    await build_and_bind_services(bot, dispatcher)


    # Регистрация обработчиков событий жизненного цикла программы
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)



