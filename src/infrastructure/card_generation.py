import logging
import os
import aiofiles
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Tuple
from playwright.async_api import Browser, Page
from jinja2 import Environment, FileSystemLoader, select_autoescape
from config import config

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
    def __init__(self, browser: Browser):
        self.browser = browser
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )

    
    async def get_page(self) -> Page:
        """Получение новой страницы"""
        page = await self.browser.new_page()
        return page

    
    async def render_card(
        self,
        template_name: str,
        data: Dict,
        size: Tuple[int, int],
    ) -> bytes:
        """
        Генерация карточки с учетом платформы и типа
        """
        try:
            # Определяем размер
            width, height = size
            
            # 3. Определяем контекст (данные) для шаблона.
            # Мы сохраняем логику значений по умолчанию из вашего
            # старого .format(), чтобы ничего не сломалось.
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
            context = {**defaults, **data}

            # 4. Получаем шаблон из окружения Jinja и рендерим его
            template_filename = template_name + ".html"
            template = self.jinja_env.get_template(template_filename)
            
            # .render() подставляет данные из 'context' в шаблон
            html_content = template.render(context)
            
            # Рендерим страницу
            page = await self.get_page()
            await page.set_viewport_size({"width": width, "height": height})
            
            # Устанавливаем контент
            await page.set_content(html_content, timeout=config.PLAYWRIGHT_TIMEOUT)
            
            # Добавляем задержку для полной загрузки стилей
            await page.wait_for_timeout(1000)
            
            # Делаем скриншот
            screenshot_bytes = await page.screenshot(
                type='png',
                # quality=100,
                full_page=False
            )
            
            await page.close()
            
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"Ошибка генерации карточки: {e}")
            raise