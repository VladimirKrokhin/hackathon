import logging
import asyncio
import aiohttp
from aiohttp import web
import threading
import socket
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from playwright.async_api import BrowserContext, async_playwright, Browser
from playwright.async_api import Playwright


from config import config
from bot.handlers import router
from infrastructure.prompt_builder import YandexGPTPromptBuilder
from infrastructure.response_processor import YandexGPTResponseProcessor
from infrastructure.card_generation import PlaywrightCardGenerator, TEMPLATES_DIR
from services.content_generation import TextContentGenerationService
from services.card_generation import CardGenerationService
from infrastructure.gpt import YandexGPT
from infrastructure.database import init_database, get_db_session
from infrastructure.repositories.ngo_repository import NGORepository
from services.ngo_service import NGOService
from infrastructure.image_generation import create_fusion_brain_image_generator
from services.image_generation import ImageGenerationService



logger = logging.getLogger(__name__)


class HTTPServerManager:
    """Менеджер HTTP-сервера для обслуживания шаблонов Playwright."""

    def __init__(self, templates_dir: Path, port: int = 8000):
        self.templates_dir = templates_dir
        self.port = port
        self.server_thread = None
        self.server = None
        self.loop = None

    def _check_port_available(self) -> bool:
        """Проверка доступности порта."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('127.0.0.1', self.port))
                sock.close()
                return True
        except OSError:
            return False

    async def _start_http_server_async(self):
        """Запуск HTTP-сервера в асинхронном режиме."""

        async def handle_request(request):
            """Обработчик запросов."""
            file_path = self.templates_dir / request.match_info['filename']

            # Проверка безопасности - файл должен быть в templates_dir
            if not str(file_path).startswith(str(self.templates_dir)):
                return web.Response(status=403, text="Access denied")

            if not file_path.exists():
                return web.Response(status=404, text="File not found")

            try:
                with open(file_path, 'rb') as f:
                    content = f.read()

                # Определение MIME-типа и charset
                if file_path.suffix.lower() == '.html':
                    content_type = 'text/html'
                    charset = 'utf-8'
                elif file_path.suffix.lower() == '.css':
                    content_type = 'text/css'
                    charset = 'utf-8'
                elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
                    content_type = 'image/' + file_path.suffix[1:].lower()
                    charset = None
                elif file_path.suffix.lower() == '.svg':
                    content_type = 'image/svg+xml'
                    charset = None
                else:
                    content_type = 'application/octet-stream'
                    charset = None

                if charset:
                    return web.Response(body=content, content_type=content_type, charset=charset)
                else:
                    return web.Response(body=content, content_type=content_type)

            except Exception as e:
                logger.error(f"Error serving {file_path}: {e}")
                return web.Response(status=500, text="Internal server error")

        app = web.Application()
        app.router.add_get('/{filename:.*}', handle_request)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, '127.0.0.1', self.port)
        await site.start()

        logger.info(f"HTTP-сервер запущен на http://127.0.0.1:{self.port} для директории {self.templates_dir}")

        # Сохраняем ссылки для остановки
        self.server = runner
        self.site = site

        # Бесконечный цикл поддержания сервера
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await runner.cleanup()
            logger.info("HTTP-сервер остановлен")

    def start_in_thread(self):
        """Запуск HTTP-сервера в отдельном потоке."""
        if not self._check_port_available():
            logger.warning(f"Порт {self.port} уже занят. HTTP-сервер не запущен.")
            return False

        def run_server():
            """Функция для запуска сервера в потоке."""
            try:
                asyncio.run(self._start_http_server_async())
            except Exception as e:
                logger.error(f"Ошибка запуска HTTP-сервера: {e}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"HTTP-сервер поток запущен на порту {self.port}")
        return True

    async def stop(self):
        """Остановка HTTP-сервера."""
        if self.server:
            await self.server.cleanup()
            logger.info("HTTP-сервер остановлен")


# Глобальный экземпляр менеджера HTTP-сервера
http_server_manager = HTTPServerManager(TEMPLATES_DIR, port=8000)



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

    dp = dispatcher

    browser, playwright = await init_browser()

    dp["browser"]: Browser = browser
    dp["playwright"]: Playwright = playwright

    dp["on_shutdown"] = lambda: close_browser(browser, playwright)
    

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

    # Запуск HTTP-сервера для Playwright
    logger.info("Запуск HTTP-сервера для обслуживания шаблонов...")
    server_started = http_server_manager.start_in_thread()
    if server_started:
        logger.info("HTTP-сервер успешно запущен")
    else:
        logger.warning("HTTP-сервер не удалось запустить - возможны проблемы с генерацией карточек")

    await build_services(bot, dispatcher)




async def on_shutdown(bot: Bot, dispatcher: Dispatcher, bots: tuple[Bot, ...], router: Router):
    """Действия при остановке бота."""
    logger.info("Завершение работы бота")

    dp = dispatcher

    # Останавливаем HTTP-сервер
    logger.info("Остановка HTTP-сервера...")
    await http_server_manager.stop()

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
