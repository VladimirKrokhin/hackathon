import logging
import asyncio
import aiohttp
from aiohttp import web
import threading
import socket
from pathlib import Path
import aiofiles
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Tuple
from playwright.async_api import Browser, BrowserContext, Page
from jinja2 import Environment, FileSystemLoader, select_autoescape
from config import config
from app import dp

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

logger = logging.getLogger(__name__)

class BaseCardGenerator(ABC):
    """Общая функциональность генераторов карточек."""

    @abstractmethod
    async def render_card(
        self,
        template_name: str,
        data: Dict,
        size: Tuple[int, int],
    ) -> bytes:
        """Генерация карточки."""
        pass


class PlaywrightCardGenerator(BaseCardGenerator):
    """
    Генерирует карточки с помощью Playwright и Jinja2.
    """

    def __init__(self, browser: Browser):
        self.browser = browser
        
        # Настраиваем окружение Jinja2 для загрузки HTML-шаблонов
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        logger.info(f"Jinja2 Environment настроен на {TEMPLATES_DIR.resolve()}")

    
    async def render_card(
        self,
        template_name: str,
        data: Dict,
        size: Tuple[int, int],
    ) -> bytes:
        """
        Генерация карточки в изолированном контексте с использованием HTTP-сервера
        для корректной загрузки ресурсов (изображений, стилей).
        """
        
        context: BrowserContext | None = None
        page: Page | None = None
        temp_file_path: Path | None = None
        
        try:
            if not self.browser.is_connected():
                logger.error("Браузер был отключен! Невозможно создать карточку.")
                raise Exception("Браузер не подключен.")

            last_context: BrowserContext = dp.get("browser_context")
            if last_context:
                await last_context.close()

            context = await self.browser.new_context()
            dp["browser_context"]: BrowserContext = context
            
            page = await context.new_page()

            # Определяем размер
            width, height = size
            
            # Определяем данные (контекст) для Jinja-шаблона
            defaults = {
                'title': 'Контент от НКО',
                'subtitle': '',
                'content': '',
                'footer': 'НКО',
                'primary_color': '#667eea',
                'secondary_color': '#764ba2',
                'text_color': '#333',
                'background_color': '#f5f7fa',
                'org_name': 'НКО',
                'contact_info': '',
                'stats': [],
                'cta_text': '',
                'cta_link': '#'
            }

            # Данные из 'data' перезапишут значения по умолчанию
            template_data = {**defaults, **data}

            # Детальная отладка данных шаблона
            logger.info("=== JINJA2 TEMPLATE DATA DEBUG ===")
            for key, value in template_data.items():
                if key == 'background_image' and isinstance(value, str) and len(value) > 100:
                    logger.info(f"{key}: [base64 image data, {len(value)} chars]")
                else:
                    logger.info(f"{key}: '{value}' (type: {type(value).__name__})")

            # Проверяем критические переменные
            critical_vars = ['title', 'content', 'org_name']
            for var in critical_vars:
                if not template_data.get(var):
                    logger.warning(f"Критическая переменная '{var}' пуста или отсутствует!")

            # Получаем шаблон Jinja и рендерим его
            template_filename = template_name + ".html"
            template = self.jinja_env.get_template(template_filename)
            html_content = template.render(template_data)

            # Логируем информацию для отладки
            logger.info(f"Jinja2 template: {template_filename}")
            logger.info(f"Template data keys: {list(template_data.keys())}")
            logger.info(f"HTML content length: {len(html_content)} chars")

            # Журналируем первые 1000 символов отрендеренного HTML для отладки
            logger.info(f"HTML content preview: {html_content[:1000]}...")
            if 'Карточка' not in html_content and template_data.get('title'):
                logger.warning("Отсутствие заголовка в HTML!")
            if 'НКО' not in html_content and template_data.get('org_name'):
                logger.warning("Отсутствие названия организации в HTML!")

            # Создаем временный HTML файл для правильной загрузки ресурсов
            unique_id = str(int(time.time() * 1000)) + str(uuid.uuid4())[:8]
            temp_filename = f"temp_card_{unique_id}.html"
            temp_file_path = TEMPLATES_DIR / temp_filename

            # Записываем HTML в файл
            async with aiofiles.open(temp_file_path, 'w', encoding='utf-8') as f:
                await f.write(html_content)

            logger.info(f"Created temp file: {temp_filename}")
            
            # Настраиваем размер
            await page.set_viewport_size({"width": width, "height": height})
            
            # Загружаем HTML через HTTP для корректной загрузки ресурсов
            await page.goto(f"http://localhost:8000/{temp_filename}", wait_until="networkidle")
            
            # Ждем загрузки всех ресурсов
            await page.wait_for_load_state("networkidle")
            
            # Делаем скриншот
            screenshot_bytes = await page.screenshot(
                type='png',
                full_page=False
            )
            
            logger.info(f"Успешно сгенерирован скриншот для {template_name}")
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"Ошибка генерации карточки '{template_name}': {e}")
            raise # Пробрасываем ошибку выше, чтобы ее обработал хэндлер
            
        finally:
            # Закрываем страницу и контекст, освобождая ресурсы.
            if page:
                await page.close()
            if context:
                await context.close()
            # Удаляем временный файл
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                    logger.info(f"Удален временный файл: {temp_file_path.name}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {temp_file_path}: {e}")

            # Удаляем временное фоновое изображение если оно было указано
            if data.get("background_image_path"):
                try:
                    bg_image_path = Path(data["background_image_path"])
                    if bg_image_path.exists():
                        bg_image_path.unlink()
                        logger.info(f"Удалено временное фоновое изображение: {bg_image_path.name}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временное фоновое изображение {data.get('background_image_path')}: {e}")


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


