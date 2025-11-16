import logging
import os
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

TEMPLATES_DIR = Path("templates")

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

            # Получаем шаблон Jinja и рендерим его
            template_filename = template_name + ".html"
            template = self.jinja_env.get_template(template_filename)
            html_content = template.render(template_data)
            
            # Создаем временный HTML файл для правильной загрузки ресурсов
            unique_id = str(int(time.time() * 1000)) + str(uuid.uuid4())[:8]
            temp_filename = f"temp_card_{unique_id}.html"
            temp_file_path = TEMPLATES_DIR / temp_filename
            
            # Записываем HTML в файл
            async with aiofiles.open(temp_file_path, 'w', encoding='utf-8') as f:
                await f.write(html_content)
            
            logger.info(f"Создан временный файл: {temp_filename}")
            
            # Настраиваем размер
            await page.set_viewport_size({"width": width, "height": height})
            
            # Загружаем HTML через HTTP для корректной загрузки ресурсов
            await page.goto(f"http://localhost:8000/{temp_filename}", wait_until="load")
            
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
