"""
Инфраструктура генерации карточек для социальных сетей.

Данный модуль предоставляет интерфейсы и реализации для создания
карточек различными способами:
- PlaywrightCardGenerator: генерация с помощью браузера и Jinja2 шаблонов
- PILCardGenerator: генерация с помощью библиотеки Pillow (PIL)
- HTTPServerManager: управление HTTP-сервером для обслуживания шаблонов

Модуль поддерживает создание карточек для различных платформ
включая Telegram, ВКонтакте и веб-сайты.
"""

import logging
import asyncio
import aiohttp
from aiohttp import web
import threading
import socket
import os
from pathlib import Path
import aiofiles
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Tuple, List
import textwrap
import re
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor, ImageOps
from playwright.async_api import Browser, BrowserContext, Page
from jinja2 import Environment, FileSystemLoader, select_autoescape
from config import config
from bot.app import dp

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

logger = logging.getLogger(__name__)


class BaseCardGenerator(ABC):
    """
    Базовый абстрактный класс для генераторов карточек.
    
    Определяет интерфейс для всех генераторов карточек,
    которые могут создавать визуальный контент для различных платформ.
    """

    @abstractmethod
    async def render_card(
        self,
        template_name: str,
        data: Dict,
        size: Tuple[int, int],
    ) -> bytes:
        """
        Генерация карточки по шаблону с заданными данными.
        
        Args:
            template_name (str): Имя HTML шаблона для рендеринга
            data (Dict): Данные для подстановки в шаблон
            size (Tuple[int, int]): Размер карточки (ширина, высота)
            
        Returns:
            bytes: Изображение карточки в формате PNG
            
        Raises:
            Exception: При ошибке генерации карточки
        """
        pass


class PlaywrightCardGenerator(BaseCardGenerator):
    """
    Генератор карточек с использованием Playwright и Jinja2.
    
    Использует браузерную автоматизацию для создания карточек
    на основе HTML шаблонов с Jinja2. Подходит для сложных
    дизайнов с CSS и JavaScript.
    """

    def __init__(self, browser: Browser):
        """
        Инициализация генератора карточек Playwright.
        
        Args:
            browser (Browser): Экземпляр браузера Playwright
        """
        self.browser = browser
        
        # Настройка окружения Jinja2 для загрузки HTML шаблонов
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        logger.info(f"Jinja2 окружение настроено для {TEMPLATES_DIR.resolve()}")

    
    async def render_card(
        self,
        template_name: str,
        data: Dict,
        size: Tuple[int, int],
    ) -> bytes:
        """
        Генерация карточки в изолированном контексте с использованием HTTP-сервера.
        
        Создает карточку с помощью браузера, используя временный HTTP-сервер
        для корректной загрузки ресурсов (изображений, стилей, шрифтов).
        
        Args:
            template_name (str): Имя HTML шаблона без расширения
            data (Dict): Данные для подстановки в шаблон
            size (Tuple[int, int]): Размер карточки (ширина, высота)
            
        Returns:
            bytes: Скриншот карточки в формате PNG
            
        Raises:
            Exception: При ошибке генерации или недоступности браузера
        """
        context: BrowserContext | None = None
        page: Page | None = None
        temp_file_path: Path | None = None
        
        try:
            if not self.browser.is_connected():
                logger.error("Браузер отключен! Невозможно создать карточку.")
                raise Exception("Браузер не подключен.")

            # Закрываем предыдущий контекст если есть
            last_context: BrowserContext = dp.get("browser_context")
            if last_context:
                await last_context.close()

            # Создаем новый контекст и страницу
            context = await self.browser.new_context()
            dp["browser_context"]: BrowserContext = context
            
            page = await context.new_page()

            # Определяем размер
            width, height = size
            
            # Значения по умолчанию для шаблона
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

            # Объединяем данные пользователя с defaults
            template_data = {**defaults, **data}

            # Логирование данных шаблона для отладки
            logger.info("=== JINJA2 ДАННЫЕ ШАБЛОНА ===")
            for key, value in template_data.items():
                if key == 'background_image' and isinstance(value, str) and len(value) > 100:
                    logger.info(f"{key}: [base64 изображение, {len(value)} символов]")
                else:
                    logger.info(f"{key}: '{value}' (тип: {type(value).__name__})")

            # Проверка критических переменных
            critical_vars = ['title', 'content', 'org_name']
            for var in critical_vars:
                if not template_data.get(var):
                    logger.warning(f"Критическая переменная '{var}' пуста или отсутствует!")

            # Получаем шаблон Jinja и рендерим его
            template_filename = template_name + ".html"
            template = self.jinja_env.get_template(template_filename)
            html_content = template.render(template_data)

            # Логирование информации для отладки
            logger.info(f"Jinja2 шаблон: {template_filename}")
            logger.info(f"Ключи данных шаблона: {list(template_data.keys())}")
            logger.info(f"Длина HTML контента: {len(html_content)} символов")

            # Логирование первых 1000 символов HTML для отладки
            logger.info(f"Превью HTML контента: {html_content[:1000]}...")
            if 'Карточка' not in html_content and template_data.get('title'):
                logger.warning("Отсутствие заголовка в HTML!")
            if 'НКО' not in html_content and template_data.get('org_name'):
                logger.warning("Отсутствие названия организации в HTML!")

            # Создание временного HTML файла для корректной загрузки ресурсов
            unique_id = str(int(time.time() * 1000)) + str(uuid.uuid4())[:8]
            temp_filename = f"temp_card_{unique_id}.html"
            temp_file_path = TEMPLATES_DIR / temp_filename

            # Запись HTML в файл
            async with aiofiles.open(temp_file_path, 'w', encoding='utf-8') as f:
                await f.write(html_content)

            logger.info(f"Создан временный файл: {temp_filename}")
            
            # Настройка размера viewport
            await page.set_viewport_size({"width": width, "height": height})
            
            # Загрузка HTML через HTTP для корректной загрузки ресурсов
            await page.goto(f"http://localhost:8000/{temp_filename}", wait_until="networkidle")
            
            # Ожидание загрузки всех ресурсов
            await page.wait_for_load_state("networkidle")
            
            # Создание скриншота
            screenshot_bytes = await page.screenshot(
                type='png',
                full_page=False
            )
            
            logger.info(f"Успешно сгенерирован скриншот для {template_name}")
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"Ошибка генерации карточки '{template_name}': {e}")
            raise # Пробрасываем ошибку выше для обработки хендлером
            
        finally:
            # Закрываем страницу и контекст, освобождая ресурсы
            if page:
                await page.close()
            if context:
                await context.close()
            # Удаление временного файла
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                    logger.info(f"Удален временный файл: {temp_file_path.name}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {temp_file_path}: {e}")

            # Удаление временного фонового изображения если оно было указано
            if data.get("background_image_path"):
                try:
                    bg_image_path = Path(data["background_image_path"])
                    if bg_image_path.exists():
                        bg_image_path.unlink()
                        logger.info(f"Удалено временное фоновое изображение: {bg_image_path.name}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временное фоновое изображение {data.get('background_image_path')}: {e}")


class PILCardGenerator(BaseCardGenerator):
    """
    Генератор карточек с использованием Pillow (PIL).
    """

    def __init__(self):
        # Кэш для шрифтов
        self.font_cache = {}

        # Попытка загрузить шрифты из системы
        self._load_fonts()

        logger.info("PILCardGenerator инициализирован")

    def _load_fonts(self):
        """
        Загрузка шрифтов.
        """
        try:
            # Расширенный список шрифтов с поддержкой кириллицы
            font_candidates = [
                # Linux шрифты (Noto Sans - лучший вариант для кириллицы)
                ("/usr/share/fonts/noto/NotoSans-Bold.ttf", "bold"),
                ("/usr/share/fonts/noto/NotoSans-Regular.ttf", "regular"),

                # Альтернативные Linux шрифты
                ("/usr/share/fonts/liberation/LiberationSans-Bold.ttf", "bold"),
                ("/usr/share/fonts/liberation/LiberationSans-Regular.ttf", "regular"),
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "bold"),
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "regular"),

                # Adwaita (GNOME default)
                ("/usr/share/fonts/Adwaita/AdwaitaSans-Bold.ttf", "bold"),
                ("/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf", "regular"),

                # macOS шрифты
                ("/System/Library/Fonts/Arial Bold.ttf", "bold"),
                ("/System/Library/Fonts/Arial.ttf", "regular"),

                # Windows шрифты
                ("C:\\Windows\\Fonts\\arialbd.ttf", "bold"),
                ("C:\\Windows\\Fonts\\arial.ttf", "regular"),
            ]

            self.bold_font_path = None
            self.regular_font_path = None

            # Поиск доступных шрифтов
            for font_path, font_type in font_candidates:
                if Path(font_path).exists():
                    if font_type == "bold":
                        self.bold_font_path = font_path
                    elif font_type == "regular":
                        self.regular_font_path = font_path

            logger.info(f"Шрифты загружены: regular={self.regular_font_path}, bold={self.bold_font_path}")

            # Тестирование загрузки шрифтов
            try:
                if self.regular_font_path:
                    test_font = self._get_font(12, False)
                    # Тестирование с кириллицей
                    test_bbox = test_font.getbbox("Тест")
                    logger.info(f"Шрифт regular протестирован: bbox={test_bbox}")

                if self.bold_font_path:
                    test_font_bold = self._get_font(12, True)
                    test_bbox_bold = test_font_bold.getbbox("Тест")
                    logger.info(f"Шрифт bold протестирован: bbox={test_bbox_bold}")

            except Exception as e:
                logger.warning(f"Ошибка при тестировании шрифтов: {e}")

        except Exception as e:
            logger.warning(f"Ошибка при загрузке шрифтов: {e}")
            self.regular_font_path = None
            self.bold_font_path = None

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """
        Получение шрифта из кэша или создание нового.
        
        Args:
            size (int): Размер шрифта
            bold (bool): Использовать жирный шрифт
            
        Returns:
            ImageFont.FreeTypeFont: Экземпляр шрифта
        """
        cache_key = f"{'bold' if bold else 'regular'}_{size}"

        if cache_key not in self.font_cache:
            font_path = self.bold_font_path if bold else self.regular_font_path
            try:
                if font_path:
                    self.font_cache[cache_key] = ImageFont.truetype(font_path, size)
                else:
                    self.font_cache[cache_key] = ImageFont.load_default()
            except Exception as e:
                logger.warning(f"Ошибка загрузки шрифта {font_path}: {e}")
                self.font_cache[cache_key] = ImageFont.load_default()

        return self.font_cache[cache_key]

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """
        Конвертация hex цвета в RGB.
        
        Args:
            hex_color (str): Цвет в hex формате (например, '#667eea')
            
        Returns:
            Tuple[int, int, int]: RGB кортеж
        """
        try:
            return ImageColor.getrgb(hex_color)
        except Exception as e:
            logger.warning(f"Ошибка парсинга цвета {hex_color}: {e}")
            return (102, 126, 234)  # default primary_color

    def _create_gradient_background(self, width: int, height: int, start_color: str, end_color: str) -> Image.Image:
        """
        Создание градиентного фона.
        
        Args:
            width (int): Ширина изображения
            height (int): Высота изображения
            start_color (str): Начальный цвет в hex
            end_color (str): Конечный цвет в hex
            
        Returns:
            Image.Image: Изображение с градиентом
        """
        start_rgb = self._hex_to_rgb(start_color)
        end_rgb = self._hex_to_rgb(end_color)

        # Создание градиентного изображения
        gradient = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(gradient)

        for y in range(height):
            # Интерполяция цвета по вертикали
            ratio = y / max(height - 1, 1)
            r = int(start_rgb[0] * (1 - ratio) + end_rgb[0] * ratio)
            g = int(start_rgb[1] * (1 - ratio) + end_rgb[1] * ratio)
            b = int(start_rgb[2] * (1 - ratio) + end_rgb[2] * ratio)

            draw.line([(0, y), (width, y)], fill=(r, g, b))

        return gradient

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        """
        Перенос текста по словам с учетом максимальной ширины.
        
        Args:
            text (str): Исходный текст
            font (ImageFont.FreeTypeFont): Шрифт для расчета ширины
            max_width (int): Максимальная ширина строки
            
        Returns:
            str: Текст с переносами строк
        """
        if not text:
            return ""

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            # Проверка ширины текущей линии с новым словом
            test_line = current_line + (" " if current_line else "") + word
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width and '\n' not in word:
                current_line = test_line
            else:
                # Новая линия или перенос по слову
                if current_line:
                    lines.append(current_line)
                if '\n' in word:
                    # Разбиение слова с переносом
                    word_parts = word.split('\n')
                    current_line = word_parts[-1]  # Последняя часть - начало новой линии
                    lines.extend(word_parts[:-1])  # Остальные части добавляем как отдельные линии
                else:
                    current_line = word

        if current_line:
            lines.append(current_line)

        return '\n'.join(lines)

    def _safe_wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """
        Безопасный перенос текста с гарантией помещения в max_width.
        
        Args:
            text (str): Исходный текст
            font (ImageFont.FreeTypeFont): Шрифт для расчета ширины
            max_width (int): Максимальная ширина строки
            
        Returns:
            List[str]: Список строк, каждая гарантированно помещается по ширине
        """
        if not text:
            return []

        # Использование textwrap для базового переноса
        import textwrap

        # Приблизительный расчет ширины символа
        avg_char_width = font.getbbox("W")[2] - font.getbbox("W")[0] + 2
        max_chars = max(1, int(max_width / avg_char_width))

        wrapped_lines = textwrap.wrap(text, width=max_chars)
        if not wrapped_lines:
            return []

        safe_lines = []

        for line in wrapped_lines:
            # Проверка ширины каждой строки
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                safe_lines.append(line)
            else:
                # Порезка строки посимвольно если все равно слишком широкая
                current_line = ""
                for char in line:
                    test_line = current_line + char
                    bbox = font.getbbox(test_line)
                    if bbox[2] - bbox[0] <= max_width - 4:  # -4 для запаса
                        current_line = test_line
                    else:
                        if current_line:
                            safe_lines.append(current_line)
                        current_line = char

                if current_line:
                    safe_lines.append(current_line)

        return safe_lines

    async def render_card(
        self,
        template_name: str,
        data: Dict,
        size: Tuple[int, int],
    ) -> bytes:
        """
        Генерация карточки с помощью Pillow.
        
        Создает карточку программно, поддерживает:
        - Стандартные карточки с градиентами и текстом
        - Специальные Telegram карточки с адаптивным дизайном
        - Поддержку Markdown форматирования
        
        Args:
            template_name (str): Имя шаблона ('telegram_post' для специальных Telegram карточек)
            data (Dict): Данные для карточки
            size (Tuple[int, int]): Размер карточки (ширина, высота)
            
        Returns:
            bytes: Изображение карточки в формате PNG
            
        Raises:
            Exception: При ошибке генерации карточки
        """
        # Проверяем, является ли это запросом на генерацию Telegram-карточки
        if template_name == 'telegram_post':
            return await self._render_telegram_card(data, size)

        # Стандартная генерация PIL-карточки
        try:
            width, height = size

            # Получение данных с значениями по умолчанию
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

            template_data = {**defaults, **data}

            logger.info(f"Генерация карточки PIL: {template_name}, размер {width}x{height}")

            # Создание основного изображения
            img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # 1. ФОН - Градиент или фоновое изображение
            gradient_bg = self._create_gradient_background(
                width, height,
                template_data['primary_color'],
                template_data['secondary_color']
            )

            # Проверка background_image_bytes и background_image_url
            background_img = None
            if template_data.get('background_image_bytes'):
                try:
                    bg_bytes = template_data['background_image_bytes']
                    background_img = Image.open(io.BytesIO(bg_bytes))
                    background_img = background_img.convert('RGBA').resize((width, height), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
                    logger.info("Фоновое изображение обработано из bytes")
                except Exception as e:
                    logger.warning(f"Ошибка обработки фонового изображения из bytes: {e}")
            elif template_data.get('background_image_url'):
                try:
                    bg_path = Path(template_data['background_image_url'])
                    if bg_path.exists():
                        background_img = Image.open(bg_path).convert('RGBA')
                        background_img = background_img.resize((width, height), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
                        logger.info("Фоновое изображение обработано из URL/пути")
                except Exception as e:
                    logger.warning(f"Ошибка загрузки фонового изображения: {e}")

            # Наложение фонового изображения на градиент
            if background_img:
                img.paste(gradient_bg, (0, 0))
                img.paste(background_img, (0, 0))

                # Создание темного оверлея для читаемости текста (40% opacity)
                overlay = Image.new('RGBA', (width, height), (0, 0, 0, 102))
                img = Image.alpha_composite(img, overlay)
            else:
                img.paste(gradient_bg, (0, 0))

            draw = ImageDraw.Draw(img)

            # 2. Основная карточка (центрированная белая область)
            card_width = int(width * 0.9)   # 90% ширины
            card_height = int(height * 0.9) # 90% высоты
            card_x = (width - card_width) // 2
            card_y = (height - card_height) // 2

            # Рисование закругленного прямоугольника (белый с тенью)
            card_bg = Image.new('RGBA', (card_width, card_height), (255, 255, 255, 230))
            # Простая тень
            shadow = Image.new('RGBA', (card_width + 4, card_height + 4), (0, 0, 0, 50))
            img.paste(shadow, (card_x - 2, card_y - 2), shadow)
            img.paste(card_bg, (card_x, card_y), card_bg)

            # Рабочая область - внутри карточки с отступами
            content_x = card_x + 50
            content_y = card_y + 40
            content_width = card_width - 100
            content_height = card_height - 80

            current_y = content_y

            # 3. ЗАГОЛОВОК
            if template_data.get('title'):
                title_font = self._get_font(48, bold=True)
                title_lines = self._wrap_text(template_data['title'], title_font, content_width)
                title_color = self._hex_to_rgb(template_data['primary_color'])

                self._draw_multiline_text(
                    draw, title_lines,
                    (content_x, current_y),
                    title_font, title_color
                )

                bbox = title_font.getbbox("Ag")
                title_height = (title_lines.count('\n') + 1) * (bbox[3] - bbox[1] + 10)
                current_y += title_height + 15

            # 4. ПОДЗАГОЛОВОК
            if template_data.get('subtitle'):
                subtitle_font = self._get_font(28)
                subtitle_lines = self._wrap_text(template_data['subtitle'], subtitle_font, content_width)
                subtitle_color = (120, 120, 120)

                self._draw_multiline_text(
                    draw, subtitle_lines,
                    (content_x, current_y),
                    subtitle_font, subtitle_color
                )

                bbox = subtitle_font.getbbox("Ag")
                subtitle_height = (subtitle_lines.count('\n') + 1) * (bbox[3] - bbox[1] + 8)
                current_y += subtitle_height + 25

            # 5. ОСНОВНОЙ КОНТЕНТ с поддержкой Markdown
            if template_data.get('content'):
                content_font = self._get_font(24)
                content_lines = self._format_markdown_text(template_data['content'], content_font, content_width)
                content_color = self._hex_to_rgb(template_data['text_color'])

                self._draw_formatted_multiline_text(
                    draw, content_lines,
                    (content_x, current_y),
                    content_font, content_color
                )

                content_height = len(content_lines) * (content_font.getbbox("Ag")[3] - content_font.getbbox("Ag")[1] + 8)
                current_y += content_height + 35

            # 6. СТАТИСТИКА (сетка)
            stats = template_data.get('stats', [])
            if stats:
                stat_card_width = min(200, content_width // 2 - 10)
                stat_card_height = 80

                # Вычисление сетки
                items_per_row = max(1, content_width // (stat_card_width + 10))
                current_stat_x = content_x

                for i, stat in enumerate(stats[:6]):  # Максимум 6 элементов
                    if i > 0 and i % items_per_row == 0:
                        current_stat_x = content_x
                        current_y += stat_card_height + 10

                    # Карточка статистики
                    stat_bg = Image.new('RGBA', (stat_card_width, stat_card_height),
                                      (248, 249, 250, 200))
                    img.paste(stat_bg, (current_stat_x, current_y), stat_bg)

                    # Число
                    number_font = self._get_font(48, bold=True)
                    number_color = self._hex_to_rgb(template_data['primary_color'])
                    number_bbox = number_font.getbbox(stat.get('number', '0'))
                    number_x = current_stat_x + stat_card_width // 2 - (number_bbox[2] - number_bbox[0]) // 2
                    number_y = current_y + 10
                    draw.text((number_x, number_y), str(stat.get('number', '0')),
                            font=number_font, fill=number_color)

                    # Лейбл
                    label_font = self._get_font(18)
                    label_text = self._wrap_text(stat.get('label', ''), label_font, stat_card_width - 10)
                    label_x = current_stat_x + stat_card_width // 2
                    label_y = current_y + 55
                    self._draw_multiline_text(
                        draw, label_text, (label_x, label_y),
                        label_font, (102, 102, 102), anchor="mt"
                    )

                    current_stat_x += stat_card_width + 10

                current_y += stat_card_height + 20

            # 7. CTA КНОПКА
            if template_data.get('cta_text'):
                button_width = 300
                button_height = 50
                button_x = content_x + (content_width - button_width) // 2
                button_y = current_y

                # Кнопка с градиентом
                button_gradient = self._create_gradient_background(
                    button_width, button_height,
                    template_data['primary_color'],
                    template_data['secondary_color']
                )

                # Закругленные углы
                mask = Image.new('L', (button_width, button_height), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([(0, 0), (button_width, button_height)], 25, fill=255)
                button_img = Image.new('RGBA', (button_width, button_height))
                button_img.paste(button_gradient, (0, 0))
                img.paste(button_img, (button_x, button_y), mask)

                # Текст кнопки
                button_font = self._get_font(20, bold=True)
                bbox = button_font.getbbox(template_data['cta_text'])
                text_width = bbox[2] - bbox[0]
                text_x = button_x + button_width // 2 - text_width // 2
                text_y = button_y + button_height // 2 - (bbox[3] - bbox[1]) // 2 + 2

                draw.text((text_x, text_y), template_data['cta_text'],
                        font=button_font, fill=(255, 255, 255))

                current_y += button_height + 20

            # 8. FOOTER
            footer_font = self._get_font(20)
            footer_color = self._hex_to_rgb(template_data['primary_color'])
            footer_text = template_data.get('org_name', 'НКО')
            if template_data.get('contact_info'):
                footer_text += f" • {template_data['contact_info']}"

            footer_lines = self._wrap_text(footer_text, footer_font, content_width)

            # Позиция футера - внизу карточки
            bbox = footer_font.getbbox("Ag")
            footer_height = (footer_lines.count('\n') + 1) * (bbox[3] - bbox[1] + 4)
            footer_y = card_y + card_height - footer_height - 15

            footer_x = content_x + content_width // 2
            self._draw_multiline_text(
                draw, footer_lines, (footer_x, footer_y),
                footer_font, footer_color, anchor="mt"
            )

            # Конвертирование в bytes
            from io import BytesIO
            output = BytesIO()
            img.save(output, format='PNG')
            card_bytes = output.getvalue()

            logger.info(f"Карточка PIL успешно сгенерирована: {len(card_bytes)} байт")
            return card_bytes

        except Exception as e:
            logger.error(f"Ошибка генерации PIL-карточки '{template_name}': {e}")
            raise

    def _draw_multiline_text(self, draw: ImageDraw.ImageDraw, text: str, position: Tuple[int, int],
                           font: ImageFont.FreeTypeFont, fill: Tuple[int, int, int],
                           anchor: str = "lt", align: str = "left"):
        """
        Отрисовка многострочного текста.
        
        Args:
            draw (ImageDraw.ImageDraw): Объект для рисования
            text (str): Текст для отрисовки
            position (Tuple[int, int]): Позиция текста
            font (ImageFont.FreeTypeFont): Шрифт текста
            fill (Tuple[int, int, int]): Цвет текста
            anchor (str): Якорь позиционирования ('lt', 'mt', 'mm')
            align (str): Выравнивание текста
        """
        if not text:
            return

        x, y = position
        lines = text.split('\n')
        line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + 4

        for line in lines:
            if not line.strip():
                y += line_height
                continue

            # Позиционирование в зависимости от anchor
            if anchor == "mm":  # middle middle
                bbox = font.getbbox(line)
                text_width = bbox[2] - bbox[0]
                text_x = x - text_width // 2
                text_y = y - line_height // 2
            elif anchor == "mt":  # middle top
                bbox = font.getbbox(line)
                text_width = bbox[2] - bbox[0]
                text_x = x - text_width // 2
                text_y = y
            else:  # left top (lt)
                text_x, text_y = x, y

            draw.text((text_x, text_y), line, font=font, fill=fill)
            y += line_height

    def _format_markdown_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[Tuple[str, bool, bool]]:
        """
        Парсинг простого Markdown текста и форматирование с переносами.
        
        Поддерживает:
        - **bold** текст
        - *italic* текст (пока не реализовано в PIL)
        
        Args:
            text (str): Исходный текст с markdown
            font (ImageFont.FreeTypeFont): Базовый шрифт
            max_width (int): Максимальная ширина строки
            
        Returns:
            List[Tuple[str, bool, bool]]: Список кортежей (текст, жирный, курсив)
        """
        if not text:
            return []

        # Удаление старых маркеров форматирования
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\*\*\1\*', text)  # ***text*** -> **text*
        text = re.sub(r'___(.+?)___', r'\*\*\1\*', text)        # ___text___ -> **text*

        # Разбиение на токены по правилам markdown
        tokens = []
        i = 0
        while i < len(text):
            if text[i:i+2] == '**':
                # Поиск конца bold текста
                end = text.find('**', i+2)
                if end != -1:
                    bold_text = text[i+2:end]
                    if bold_text:
                        tokens.append((bold_text, True, False))  # bold
                    i = end + 2
                else:
                    tokens.append((text[i], False, False))
                    i += 1
            elif text[i] == '*':
                # Поиск конца italic текста
                end = text.find('*', i+1)
                if end != -1:
                    italic_text = text[i+1:end]
                    if italic_text:
                        tokens.append((italic_text, False, True))  # italic
                    i = end + 1
                else:
                    tokens.append((text[i], False, False))
                    i += 1
            else:
                # Обычный текст
                chunk = ""
                while i < len(text) and text[i:i+2] != '**' and text[i] != '*':
                    chunk += text[i]
                    i += 1
                if chunk:
                    tokens.append((chunk, False, False))

        # Перенос по ширине с сохранением форматирования
        formatted_lines = []
        current_line = []
        current_width = 0

        for token_text, is_bold, is_italic in tokens:
            words = token_text.split()

            for word in words:
                test_font = self._get_font(font.size, is_bold)
                word_bbox = test_font.getbbox(word)
                word_width = word_bbox[2] - word_bbox[0]

                if current_width + word_width <= max_width or not current_line:
                    current_line.append((word, is_bold, is_italic))
                    current_width += word_width + 4
                else:
                    if current_line:
                        formatted_lines.extend(current_line)
                        formatted_lines.append(('\n', False, False))

                    current_line = [(word, is_bold, is_italic)]
                    current_width = word_width

        if current_line:
            formatted_lines.extend(current_line)

        return formatted_lines

    def _draw_formatted_multiline_text(self, draw: ImageDraw.ImageDraw,
                                     formatted_tokens: List[Tuple[str, bool, bool]],
                                     position: Tuple[int, int],
                                     base_font: ImageFont.FreeTypeFont,
                                     base_color: Tuple[int, int, int]):
        """
        Отрисовка форматированного текста с поддержкой bold/italic.
        
        Args:
            draw (ImageDraw.ImageDraw): Объект для рисования
            formatted_tokens (List[Tuple[str, bool, bool]]): Форматированные токены
            position (Tuple[int, int]): Позиция для отрисовки
            base_font (ImageFont.FreeTypeFont): Базовый шрифт
            base_color (Tuple[int, int, int]): Базовый цвет
        """
        x, y = position
        line_height = base_font.getbbox("Ag")[3] - base_font.getbbox("Ag")[1] + 6

        current_x = x

        for token_text, is_bold, is_italic in formatted_tokens:
            if token_text == '\n':
                # Новая строка
                current_x = x
                y += line_height
                continue

            # Выбор шрифта
            font = self._get_font(base_font.size, is_bold)

            # Отрисовка токена
            draw.text((current_x, y), token_text, font=font, fill=base_color)

            # Сдвиг позиции
            bbox = font.getbbox(token_text)
            current_x += bbox[2] - bbox[0] + 4


class HTTPServerManager:
    """
    Менеджер HTTP-сервера для обслуживания шаблонов Playwright.
    
    Запускает простой HTTP-сервер в отдельном потоке для
    обслуживания HTML шаблонов и статических ресурсов,
    которые нужны Playwright для корректной работы.
    """

    def __init__(self, templates_dir: Path, port: int = 8000):
        """
        Инициализация менеджера HTTP-сервера.
        
        Args:
            templates_dir (Path): Директория с шаблонами
            port (int): Порт для сервера
        """
        self.templates_dir = templates_dir
        self.port = port
        self.server_thread = None
        self.server = None
        self.loop = None

    def _check_port_available(self) -> bool:
        """
        Проверка доступности порта.
        
        Returns:
            bool: True если порт свободен
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('127.0.0.1', self.port))
                sock.close()
                return True
        except OSError:
            return False

    async def _start_http_server_async(self):
        """
        Запуск HTTP-сервера в асинхронном режиме.
        
        Создает простой HTTP сервер для обслуживания статических
        файлов и HTML шаблонов для Playwright.
        """
        async def handle_request(request):
            """Обработчик HTTP запросов."""
            file_path = self.templates_dir / request.match_info['filename']

            # Проверка безопасности - файл должен быть в templates_dir
            if not str(file_path).startswith(str(self.templates_dir)):
                return web.Response(status=403, text="Доступ запрещен")

            if not file_path.exists():
                return web.Response(status=404, text="Файл не найден")

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
                logger.error(f"Ошибка обслуживания {file_path}: {e}")
                return web.Response(status=500, text="Внутренняя ошибка сервера")

        app = web.Application()
        app.router.add_get('/{filename:.*}', handle_request)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, '127.0.0.1', self.port)
        await site.start()

        logger.info(f"HTTP-сервер запущен на http://127.0.0.1:{self.port} для директории {self.templates_dir}")

        # Сохранение ссылок для остановки
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
        """
        Запуск HTTP-сервера в отдельном потоке.
        
        Returns:
            bool: True если сервер успешно запущен
        """
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
        logger.info(f"HTTP-сервер запущен в потоке на порту {self.port}")
        return True

    async def stop(self):
        """
        Остановка HTTP-сервера.
        """
        if self.server:
            await self.server.cleanup()
            logger.info("HTTP-сервер остановлен")
