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
from typing import Dict, Tuple, List
import textwrap
import re
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor
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


class PILCardGenerator(BaseCardGenerator):
    """
    Генерирует карточки с помощью Pillow (PIL) без использования браузера.
    """

    def __init__(self):
        # Кэш для шрифтов
        self.font_cache = {}

        # Попытка загрузить шрифты из системы
        self._load_fonts()

        logger.info("PILCardGenerator инициализирован")

    def _load_fonts(self):
        """Загрузка доступных шрифтов с поддержкой кириллицы."""
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

            # Ищем доступные шрифты
            for font_path, font_type in font_candidates:
                if Path(font_path).exists():
                    if font_type == "bold":
                        self.bold_font_path = font_path
                    elif font_type == "regular":
                        self.regular_font_path = font_path

            logger.info(f"Шрифты загружены: regular={self.regular_font_path}, bold={self.bold_font_path}")

            # Тестируем загрузку шрифтов
            try:
                if self.regular_font_path:
                    test_font = self._get_font(12, False)
                    # Тестируем с кириллицей
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
        """Получение шрифта из кэша или создание нового."""
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
        """Конвертация hex цвета в RGB."""
        try:
            return ImageColor.getrgb(hex_color)
        except Exception as e:
            logger.warning(f"Ошибка парсинга цвета {hex_color}: {e}")
            return (102, 126, 234)  # default primary_color

    def _create_gradient_background(self, width: int, height: int, start_color: str, end_color: str) -> Image.Image:
        """Создание градиентного фона."""
        start_rgb = self._hex_to_rgb(start_color)
        end_rgb = self._hex_to_rgb(end_color)

        # Создаем градиентное изображение
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
        """Перенос текста по словам с учетом максимальной ширины."""
        if not text:
            return ""

        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            # Проверяем ширину текущей линии с новым словом
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
                    # Разбиваем слово с переносом
                    word_parts = word.split('\n')
                    current_line = word_parts[-1]  # Последняя часть - начало новой линии
                    lines.extend(word_parts[:-1])  # Остальные части добавляем как отдельные линии
                else:
                    current_line = word

        if current_line:
            lines.append(current_line)

        return '\n'.join(lines)

    def _draw_multiline_text(self, draw: ImageDraw.ImageDraw, text: str, position: Tuple[int, int],
                           font: ImageFont.FreeTypeFont, fill: Tuple[int, int, int],
                           anchor: str = "lt", align: str = "left"):
        """Отрисовка многострочного текста."""
        if not text:
            return

        x, y = position
        lines = text.split('\n')
        line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + 4  # Высота линии

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
        """Парсинг простого Markdown текста и форматирование с переносами.

        Поддерживает:
        - **bold** текст
        - *italic* текст (пока не реализовано в PIL, но можно добавить курсивный шрифт)

        Возвращает список кортежей: (text_chunk, is_bold, is_italic)
        """
        if not text:
            return []

        # Удаляем старые маркеры форматирования рекурсивно
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\*\*\1\*', text)  # ***text*** -> **text*
        text = re.sub(r'___(.+?)___', r'\*\*\1\*', text)        # ___text___ -> **text*

        # Разбиваем на токены по правилам markdown
        tokens = []
        i = 0
        while i < len(text):
            if text[i:i+2] == '**':
                # Найдем конец bold текста
                end = text.find('**', i+2)
                if end != -1:
                    bold_text = text[i+2:end]
                    if bold_text:
                        tokens.append((bold_text, True, False))  # bold
                    i = end + 2
                else:
                    # Не найден закрывающий маркер, добавляем как обычный текст
                    tokens.append((text[i], False, False))
                    i += 1
            elif text[i] == '*':
                # Найдем конец italic текста
                end = text.find('*', i+1)
                if end != -1:
                    italic_text = text[i+1:end]
                    if italic_text:
                        tokens.append((italic_text, False, True))  # italic (пока без курсива)
                    i = end + 1
                else:
                    # Не найден закрывающий маркер, добавляем как обычный текст
                    tokens.append((text[i], False, False))
                    i += 1
            else:
                # Обычный текст - собираем до следующего маркера
                chunk = ""
                while i < len(text) and text[i:i+2] != '**' and text[i] != '*':
                    chunk += text[i]
                    i += 1
                if chunk:
                    tokens.append((chunk, False, False))  # regular

        # Теперь переносим по ширине и сохраняем форматирование
        formatted_lines = []
        current_line = []
        current_width = 0

        for token_text, is_bold, is_italic in tokens:
            # Разбиваем токен на слова
            words = token_text.split()

            for word in words:
                # Проверяем ширину слова
                test_font = self._get_font(font.size, is_bold)  # Используем bold шрифт если нужно
                word_bbox = test_font.getbbox(word)
                word_width = word_bbox[2] - word_bbox[0]

                # Проверяем помещается ли слово в текущую строку
                if current_width + word_width <= max_width or not current_line:
                    current_line.append((word, is_bold, is_italic))
                    current_width += word_width + 4  # + отступ между словами
                else:
                    # Переходим на новую строку
                    if current_line:
                        formatted_lines.extend(current_line)
                        formatted_lines.append(('\n', False, False))  # маркер новой строки

                    current_line = [(word, is_bold, is_italic)]
                    current_width = word_width

        # Добавляем последнюю строку
        if current_line:
            formatted_lines.extend(current_line)

        return formatted_lines

    def _draw_formatted_multiline_text(self, draw: ImageDraw.ImageDraw,
                                     formatted_tokens: List[Tuple[str, bool, bool]],
                                     position: Tuple[int, int],
                                     base_font: ImageFont.FreeTypeFont,
                                     base_color: Tuple[int, int, int]):
        """Отрисовка форматированного текста с поддержкой bold/italic."""
        x, y = position
        line_height = base_font.getbbox("Ag")[3] - base_font.getbbox("Ag")[1] + 6

        current_x = x

        for token_text, is_bold, is_italic in formatted_tokens:
            if token_text == '\n':
                # Новая строка
                current_x = x
                y += line_height
                continue

            # Выбираем шрифт
            font = self._get_font(base_font.size, is_bold)

            # Рисуем токен
            draw.text((current_x, y), token_text, font=font, fill=base_color)

            # Сдвигаем позицию
            bbox = font.getbbox(token_text)
            current_x += bbox[2] - bbox[0] + 4  # + отступ между словами

    async def render_card(
        self,
        template_name: str,
        data: Dict,
        size: Tuple[int, int],
    ) -> bytes:
        """
        Генерация карточки с помощью Pillow.
        """
        try:
            width, height = size

            # Получаем данные с значениями по умолчанию
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

            # Создаем основное изображение
            img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # 1. ФОН - Градиент или фоновое изображение
            gradient_bg = self._create_gradient_background(
                width, height,
                template_data['primary_color'],
                template_data['secondary_color']
            )

            # Проверяем сначала background_image_bytes, потом background_image_url
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

            # Накладываем фоновое изображение на градиент, если оно есть
            if background_img:
                # Накладываем фоновое изображение
                img.paste(gradient_bg, (0, 0))
                img.paste(background_img, (0, 0))

                # Создаем темный оверлей для читаемости текста (40% opacity)
                overlay = Image.new('RGBA', (width, height), (0, 0, 0, 102))
                img = Image.alpha_composite(img, overlay)
            else:
                # Просто градиентный фон без изображения
                img.paste(gradient_bg, (0, 0))

            draw = ImageDraw.Draw(img)

            # 2. Основная карточка (центрированная белая область)
            card_width = int(width * 0.9)   # 90% ширины
            card_height = int(height * 0.9) # 90% высоты
            card_x = (width - card_width) // 2
            card_y = (height - card_height) // 2

            # Рисуем закругленный прямоугольник (белый с тенью)
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

            # 4. ЗАГОЛОВОК
            if template_data.get('title'):
                title_font = self._get_font(48, bold=True)  # Увеличен размер
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

            # 5. ПОДЗАГОЛОВОК
            if template_data.get('subtitle'):
                subtitle_font = self._get_font(28)  # Увеличен размер
                subtitle_lines = self._wrap_text(template_data['subtitle'], subtitle_font, content_width)
                subtitle_color = (120, 120, 120)  # Более светлый серый

                self._draw_multiline_text(
                    draw, subtitle_lines,
                    (content_x, current_y),
                    subtitle_font, subtitle_color
                )

                bbox = subtitle_font.getbbox("Ag")
                subtitle_height = (subtitle_lines.count('\n') + 1) * (bbox[3] - bbox[1] + 8)
                current_y += subtitle_height + 25

            # 6. ОСНОВНОЙ КОНТЕНТ с поддержкой Markdown
            if template_data.get('content'):
                content_font = self._get_font(24)  # Увеличен размер
                content_lines = self._format_markdown_text(template_data['content'], content_font, content_width)
                content_color = self._hex_to_rgb(template_data['text_color'])

                self._draw_formatted_multiline_text(
                    draw, content_lines,
                    (content_x, current_y),
                    content_font, content_color
                )

                content_height = len(content_lines) * (content_font.getbbox("Ag")[3] - content_font.getbbox("Ag")[1] + 8)
                current_y += content_height + 35

            # 7. СТАТИСТИКА (сетка)
            stats = template_data.get('stats', [])
            if stats:
                stat_card_width = min(200, content_width // 2 - 10)
                stat_card_height = 80

                # Вычисляем сетку
                items_per_row = max(1, content_width // (stat_card_width + 10))
                current_stat_x = content_x

                for i, stat in enumerate(stats[:6]):  # Максимум 6 элементов
                    if i > 0 and i % items_per_row == 0:
                        current_stat_x = content_x
                        current_y += stat_card_height + 10

                    # Карточка статистики
                    stat_bg = Image.new('RGBA', (stat_card_width, stat_card_height),
                                      (248, 249, 250, 200))  # Светло-серый
                    img.paste(stat_bg, (current_stat_x, current_y), stat_bg)

                    # Число
                    number_font = self._get_font(48, bold=True)  # Увеличен с 42 до 48
                    number_color = self._hex_to_rgb(template_data['primary_color'])
                    number_bbox = number_font.getbbox(stat.get('number', '0'))
                    number_x = current_stat_x + stat_card_width // 2 - (number_bbox[2] - number_bbox[0]) // 2
                    number_y = current_y + 10  # Подняты выше для лучшего баланса
                    draw.text((number_x, number_y), str(stat.get('number', '0')),
                            font=number_font, fill=number_color)

                    # Лейбл
                    label_font = self._get_font(18)  # Увеличен с 14 до 18
                    label_text = self._wrap_text(stat.get('label', ''), label_font, stat_card_width - 10)
                    label_x = current_stat_x + stat_card_width // 2
                    label_y = current_y + 55  # Ниже для лучшего размещения большого числа
                    self._draw_multiline_text(
                        draw, label_text, (label_x, label_y),
                        label_font, (102, 102, 102), anchor="mt"  # middle top
                    )

                    current_stat_x += stat_card_width + 10

                current_y += stat_card_height + 20

            # 8. CTA КНОПКА
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

                # Закругленные углы (аппроксимация через маску)
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

            # 9. FOOTER
            footer_font = self._get_font(20)  # Увеличен с 16 до 20
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
                footer_font, footer_color, anchor="mt"  # middle top
            )

            # Конвертируем в bytes
            from io import BytesIO
            output = BytesIO()
            img.save(output, format='PNG')
            card_bytes = output.getvalue()

            logger.info(f"Карточка PIL успешно сгенерирована: {len(card_bytes)} байт")
            return card_bytes

        except Exception as e:
            logger.error(f"Ошибка генерации PIL-карточки '{template_name}': {e}")
            raise


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
