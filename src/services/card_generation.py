import asyncio
import os
import io
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from playwright.async_api import async_playwright, Browser, Page
import aiofiles
from config import config

class CardGenerator:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.templates_dir = Path("templates")
        self.template_cache = {}
        self.playwright = None
        
    async def init_browser(self):
        """Инициализация браузера"""
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process"
                ]
            )
    
    async def close_browser(self):
        """Закрытие браузера"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def load_template(self, template_name: str) -> str:
        """Загрузка шаблона с кэшированием"""
        if template_name in self.template_cache:
            return self.template_cache[template_name]
        
        template_path = self.templates_dir / f"{template_name}.html"
        if not template_path.exists():
            # Используем универсальный шаблон по умолчанию
            template_path = self.templates_dir / "universal_card.html"
        
        try:
            async with aiofiles.open(template_path, "r", encoding="utf-8") as f:
                template_content = await f.read()
                self.template_cache[template_name] = template_content
                return template_content
        except Exception as e:
            print(f"Ошибка загрузки шаблона {template_name}: {e}")
            # Возвращаем базовый шаблон
            return self.get_fallback_template()
    
    def get_fallback_template(self) -> str:
        """Базовый шаблон на случай ошибки"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    height: 100vh; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    margin: 0;
                    padding: 20px;
                }
                .card {
                    background: white; 
                    border-radius: 20px; 
                    padding: 40px; 
                    text-align: center; 
                    max-width: 800px; 
                    width: 100%;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                h1 { 
                    color: #333; 
                    font-size: 2.5em; 
                    margin-bottom: 20px;
                }
                p { 
                    color: #666; 
                    font-size: 1.2em; 
                    line-height: 1.6;
                }
                .footer { 
                    margin-top: 30px; 
                    color: #999; 
                    font-style: italic;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>{title}</h1>
                <p>{content}</p>
                <div class="footer">{footer}</div>
            </div>
        </body>
        </html>
        """
    
    async def get_page(self) -> Page:
        """Получение новой страницы"""
        if not self.browser:
            await self.init_browser()
        return await self.browser.new_page()
    
    async def render_card(
        self,
        template_name: str,
        data: Dict,
        platform: str,
        card_type: str = "post",
        custom_size: Optional[Tuple[int, int]] = None
    ) -> bytes:
        """
        Генерация карточки с учетом платформы и типа
        """
        try:
            # Определяем размер
            size = self._get_size_for_platform(platform, card_type, custom_size)
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
    
    async def generate_fallback_card(self, error_text: str) -> bytes:
        """Генерация fallback карточки при ошибке"""
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        
        # Создаем простое изображение с ошибкой
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color='#667eea')
        draw = ImageDraw.Draw(img)
        
        # Рисуем текст ошибки
        draw.rectangle([50, 50, width-50, height-50], fill='white', outline='#333')
        draw.text((100, 150), "Ошибка генерации карточки", fill='#333', font_size=36)
        draw.text((100, 250), error_text[:100], fill='#666', font_size=24)
        draw.text((100, 350), "Попробуйте еще раз", fill='#667eea', font_size=28)
        
        # Конвертируем в bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    
    def _get_size_for_platform(
        self,
        platform: str,
        card_type: str,
        custom_size: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int]:
        """Определение размера на основе платформы"""
        if custom_size:
            return custom_size
        
        # Находим конфигурацию для платформы
        for platform_key, sizes in config.SOCIAL_MEDIA_SIZES.items():
            if platform_key in platform or platform in platform_key:
                # Определяем тип карточки
                if card_type == "story" and "story" in sizes:
                    return (sizes["story"]["width"], sizes["story"]["height"])
                elif card_type == "square" and "post_square" in sizes:
                    return (sizes["post_square"]["width"], sizes["post_square"]["height"])
                elif "post" in sizes:
                    return (sizes["post"]["width"], sizes["post"]["height"])
                break
        
        # Дефолтные размеры
        if card_type == "story":
            return config.DEFAULT_SIZES["story"]
        elif card_type == "square":
            return config.DEFAULT_SIZES["square"]
        return config.DEFAULT_SIZES["post"]
    
    async def generate_multiple_cards(
        self,
        template_name: str,
        data: Dict,
        platform: str
    ) -> Dict[str, bytes]:
        """
        Генерация нескольких карточек для разных форматов в зависимости от платформы
        """
        results = {}
        
        # Определяем, какие карточки генерировать для платформы
        card_types = []
        
        if "📸 Instagram" in platform:
            card_types = ["post_square", "story", "post_portrait"]
        elif "📱 ВКонтакте" in platform:
            card_types = ["post", "story"]
        elif "💬 Telegram" in platform:
            card_types = ["post"]
        else:
            card_types = ["post"]
        
        for card_type in card_types:
            try:
                image_bytes = await self.render_card(
                    template_name=template_name,
                    data=data,
                    platform=platform,
                    card_type=card_type
                )
                results[card_type] = image_bytes
            except Exception as e:
                print(f"Ошибка генерации карточки {card_type}: {e}")
                continue
        
        return results
    
    async def generate_content_preview(self, content: str, platform: str) -> bytes:
        """Генерация превью для текстового контента"""
        data = {
            'title': 'Текст поста',
            'content': content[:300] + '...' if len(content) > 300 else content,
            'footer': f'Платформа: {platform}'
        }
        return await self.render_card('universal_card', data, platform, 'post')

# Глобальный экземпляр
card_generator = CardGenerator()
