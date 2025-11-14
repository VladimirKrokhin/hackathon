from abc import ABC, abstractmethod
from typing import Dict, Tuple
from playwright.async_api import Browser, Page
from config import config


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

    async def load_template(self, template_name: str) -> str:
        """Загрузка шаблона."""
        pass



class PlaywrightCardGenerator(BaseCardGenerator):
    def __init__(self, browser: Browser):
        self.browser = browser
        

    
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
            
            # Загружаем шаблон
            template = await self.load_template(template_name)
            
            # Формируем HTML с данными
            html_content = template.format(
                title=data.get('title', 'Контент от НКО'),
                subtitle=data.get('subtitle', ''),
                content=data.get('content', ''),
                footer=data.get('footer', 'НКО'),
                primary_color=data.get('primary_color', '#667eea'),
                secondary_color=data.get('secondary_color', '#764ba2'),
                text_color=data.get('text_color', '#333'),
                background_color=data.get('background_color', '#f5f7fa'),
                org_name=data.get('org_name', 'НКО'),
                contact_info=data.get('contact_info', ''),
                stats=data.get('stats', []),
                cta_text=data.get('cta_text', ''),
                cta_link=data.get('cta_link', '#')
            )
            
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
                quality=100,
                full_page=False
            )
            
            await page.close()
            
            return screenshot_bytes
            
        except Exception as e:
            print(f"Ошибка генерации карточки: {e}")
            # Возвращаем fallback изображение
            return await self.generate_fallback_card(str(e))
    

