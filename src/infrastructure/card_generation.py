"""
Инфраструктура генерации карточек для социальных сетей.

Данный модуль предоставляет интерфейсы и реализации для создания
карточек различными способами:
- PillowCardGenerator: генерация с помощью библиотеки Pillow (PIL)

Модуль поддерживает создание карточек для различных платформ
включая Telegram, ВКонтакте и веб-сайты.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, List
import re
import io
from PIL import Image, ImageDraw, ImageFont, ImageColor

from dtos import CardData, RenderParameters

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
        parameters: RenderParameters,
        data: CardData,
    ) -> bytes:
        """
        Генерация карточки по шаблону.
        
        Args:
            paremeters (RenderParameters): Параметры для рендеринга
            data (CardData): Данные для подстановки в шаблон
            
        Returns:
            bytes: Изображение карточки в формате PNG
            
        Raises:
            Exception: При ошибке генерации карточки
        """
        pass


class PillowCardGenerator(BaseCardGenerator):
    """
    Генератор карточек с использованием Pillow (PIL).
    """

    def __init__(self):
        # Кэш для шрифтов
        self.font_cache = {}

        # Попытка загрузить шрифты из системы
        self._load_fonts()

        logger.info("PillowCardGenerator инициализирован")

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

        except Exception as e:
            logger.warning(f"Ошибка при загрузке шрифтов: {e}")
            self.regular_font_path = None
            self.bold_font_path = None
            raise


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
        parameters: RenderParameters,
        data: CardData,
    ) -> bytes:
        """
        Генерация карточки с помощью Pillow.
        
        Создает карточку программно, поддерживает:
        - Стандартные карточки с градиентами и текстом
        - Специальные Telegram карточки с адаптивным дизайном
        - Поддержку Markdown форматирования
        
        Args:
            parameters (RenderParameters): Параметры для генерации
            data (CardData): Данные для карточки
            
        Returns:
            bytes: Изображение карточки в формате PNG
            
        Raises:
            Exception: При ошибке генерации карточки
        """
        # Стандартная генерация PIL-карточки

        try:

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


