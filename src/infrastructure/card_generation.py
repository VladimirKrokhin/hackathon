"""
Инфраструктура генерации карточек для социальных сетей.

Данный модуль предоставляет интерфейсы и реализации для создания
карточек различными способами:
- PillowCardGenerator: генерация с помощью библиотеки Pillow (PIL)

Модуль поддерживает создание карточек для различных платформ
включая Telegram, ВКонтакте и веб-сайты.
"""

import logging
import os
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, List
import re
import io
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageOps

from dtos import CardData, RenderParameters, Dimensions, CardTemplate

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

    def _safe_wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Безопасный перенос текста с гарантией, что ни одна строка не выйдет за max_width.

        Возвращает список строк, каждая из которых гарантированно помещается по ширине.
        """
        if not text:
            return []

        # Сначала используем textwrap для базового переноса
        import textwrap

        # Приблизительный расчет ширины символа для textwrap (усредненный)
        avg_char_width = font.getbbox("W")[2] - font.getbbox("W")[0] + 2
        max_chars = max(1, int(max_width / avg_char_width))

        wrapped_lines = textwrap.wrap(text, width=max_chars)
        if not wrapped_lines:
            return []

        safe_lines = []

        for line in wrapped_lines:
            # Последняя проверка ширины каждой строки
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                safe_lines.append(line)
            else:
                # Если строка все равно слишком широкая, режем ее посимвольно
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

    def _format_markdown_text_telegram(self, text: str, base_font: ImageFont.FreeTypeFont, max_width: int) -> List[Tuple[str, bool, bool]]:
        """Парсинг простого Markdown текста для Telegram-карточек.

        Поддерживает:
        - **bold** текст
        - *italic* текст (placeholder для будущего расширения)

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
        formatted_tokens = []
        current_line_tokens = []
        current_width = 0

        for token_text, is_bold, is_italic in tokens:
            # Разбиваем токен на слова
            words = token_text.split()

            for word in words:
                # Проверяем ширину слова
                font = self._get_font(base_font.size, is_bold) if is_bold else base_font
                word_bbox = font.getbbox(word)
                word_width = word_bbox[2] - word_bbox[0]

                # Проверяем помещается ли слово в текущую строку
                if current_width + word_width <= max_width or not current_line_tokens:
                    current_line_tokens.append((word, is_bold, is_italic))
                    current_width += word_width + 6  # + отступ между словами
                else:
                    # Переходим на новую строку
                    if current_line_tokens:
                        formatted_tokens.extend(current_line_tokens)
                        formatted_tokens.append(('\n', False, False))  # маркер новой строки

                    current_line_tokens = [(word, is_bold, is_italic)]
                    current_width = word_width

        # Добавляем последнюю строку
        if current_line_tokens:
            formatted_tokens.extend(current_line_tokens)

        return formatted_tokens

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

    def _create_telegram_gradient(self, width, height, color1, color2):
        """Создает горизонтальный градиент для Telegram-карточек."""
        base = Image.new('RGB', (width, height), color1)
        top = Image.new('RGB', (width, height), color2)
        mask = Image.new('L', (width, height))
        mask_data = []
        for y in range(height):
            mask_data.extend([int(255 * (x / width)) for x in range(width)])
        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        return base

    def _draw_telegram_icon(self, draw, icon_type, x, y, size, color):
        """Рисует схематичные иконки для Telegram."""
        if icon_type == 'building':  # Иконка НКО
            draw.rectangle([x, y + size*0.2, x + size, y + size], fill=color)
            # Окна
            w_size = size * 0.2
            for i in range(2):
                for j in range(2):
                    draw.rectangle([x + size*0.2 + i*w_size*1.5, y + size*0.4 + j*w_size*1.5,
                                    x + size*0.2 + i*w_size*1.5 + w_size, y + size*0.4 + j*w_size*1.5 + w_size], fill=(255,255,255))

        elif icon_type == 'pin':  # Иконка локации
            cx, cy = x + size/2, y + size/3
            r = size/2.5
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)
            draw.polygon([cx, cy+r, cx-r/2, cy, cx+r/2, cy], fill=color)  # Ножка
            draw.polygon([cx, y+size, cx-2, cy+r/2, cx+2, cy+r/2], fill=color)  # Острие
            draw.ellipse([cx-r/3, cy-r/3, cx+r/3, cy+r/3], fill=(255,255,255))  # Точка внутри

        elif icon_type == 'people':  # Иконка аудитории
            # Человек 1
            draw.ellipse([x, y, x + size/3, y + size/3], fill=color)  # Голова
            draw.pieslice([x - size/6, y + size/3, x + size/2, y + size], 270, 90, fill=color)
            # Человек 2
            draw.ellipse([x + size/2, y, x + size/2 + size/3, y + size/3], fill=color)
            draw.pieslice([x + size/3, y + size/3, x + size, y + size], 270, 90, fill=color)

        elif icon_type == 'datetime':  # Иконка даты и времени
            # Рисуем календарь
            draw.rectangle([x, y, x + size, y + size], outline=color, width=2)
            # Верхняя полоса календаря
            draw.rectangle([x, y, x + size, y + size*0.3], fill=color)
            # Точки на верхней полосе (дни недели)
            dot_size = size * 0.05
            for i in range(7):
                dot_x = x + size*0.1 + i * size*0.12
                dot_y = y + size*0.15
                draw.ellipse([dot_x, dot_y, dot_x + dot_size, dot_y + dot_size], fill=(255,255,255))

    def _draw_telegram_pill(self, img, x, y, text, icon_type, font, text_color=(0,0,0), bg_color=(255,255,255)):
        """Рисует скругленную плашку с иконкой и текстом для Telegram."""
        draw = ImageDraw.Draw(img)

        # Отступы
        padding_x = 20
        padding_y = 10
        icon_size = 30
        icon_padding = 10

        # Считаем размеры текста
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Полная ширина и высота плашки
        full_w = padding_x * 2 + icon_size + icon_padding + text_w
        full_h = padding_y * 2 + text_h + 10  # +10 для запаса на высоту шрифта

        # Рисуем скругленный прямоугольник (фон)
        shape = [(x, y), (x + full_w, y + full_h)]
        draw.rounded_rectangle(shape, radius=full_h//2, fill=bg_color)

        # Рисуем иконку
        icon_x = x + padding_x
        icon_y = y + (full_h - icon_size) // 2
        self._draw_telegram_icon(draw, icon_type, icon_x, icon_y, icon_size, text_color)

        # Рисуем текст
        text_x = icon_x + icon_size + icon_padding
        text_y = y + (full_h - text_h) // 2 - 5  # -5 небольшая коррекция базовой линии
        draw.text((text_x, text_y), text, font=font, fill=text_color)

        return y + full_h + 15  # Возвращаем Y координату для следующего элемента (+ отступ)

    def _format_telegram_datetime(self, event_datetime):
        """Форматирует дату и время в читаемый формат для Telegram: '15 декабря 2025, 14:00'"""
        from datetime import datetime

        # Названия месяцев на русском
        months_ru = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
            7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }

        try:
            # Пробуем разные форматы входной даты
            formats = [
                "%Y-%m-%d %H:%M:%S",  # 2025-12-15 14:00:00
                "%Y-%m-%d %H:%M",     # 2025-12-15 14:00
                "%d.%m.%Y %H:%M",     # 15.12.2025 14:00
                "%d.%m.%Y %H:%M:%S",  # 15.12.2025 14:00:00
            ]

            dt = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(event_datetime, fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                return event_datetime

            day = dt.day
            month_name = months_ru[dt.month]
            year = dt.year
            time_str = dt.strftime("%H:%M")

            return f"{day} {month_name} {year}, {time_str}"

        except Exception as e:
            logger.warning(f"Ошибка форматирования даты '{event_datetime}': {e}")
            return event_datetime



    def _load_telegram_fonts(self):
        """Загрузка шрифтов для Telegram-карточек."""
        font_paths = {
            "arialbd.ttf": None,  # Arial Bold
            "arial.ttf": None,    # Arial Regular
            "DejaVuSans-Bold.ttf": None,
            "LiberationSans-Bold.ttf": None,
            "FreeSansBold.ttf": None,
            "DejaVuSans.ttf": None,
            "LiberationSans-Regular.ttf": None,
            "FreeSans.ttf": None
        }

        # Стандартные пути к шрифтам в Linux
        font_dirs = [
            "/usr/share/fonts",
            "/usr/share/fonts/truetype",
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/liberation",
            "/usr/share/fonts/truetype/freefont"
        ]

        # Ищем доступные шрифты
        for name in font_paths.keys():
            for folder in font_dirs:
                path = os.path.join(folder, name)
                if os.path.exists(path):
                    font_paths[name] = path
                    break

        logger.info(f"Telegram-шрифты загружены: {len([p for p in font_paths.values() if p])} найдено")
        return font_paths

    def _get_telegram_font(self, font_names, size, font_paths):
        """Перебирает список шрифтов для Telegram-карточек и загружает первый найденный."""
        for name in font_names:
            # 1. Пробуем загрузить просто по имени
            try:
                font = ImageFont.truetype(name, size)
                return font
            except OSError:
                # 2. Пробуем найти в путях
                if font_paths.get(name) and os.path.exists(font_paths[name]):
                    font = ImageFont.truetype(font_paths[name], size)
                    return font

        # Если ничего не нашли, возвращаем дефолтный
        logger.warning(f"Telegram-шрифты {font_names} не найдены. Используется стандартный.")
        return ImageFont.load_default()

    def _create_horizontal_gradient(self, width: int, height: int, color1_rgb: Tuple[int, int, int],
                                    color2_rgb: Tuple[int, int, int]) -> Image.Image:
        """
        Создание горизонтального градиента (слева направо).
        """
        base = Image.new('RGB', (width, height), color1_rgb)
        top = Image.new('RGB', (width, height), color2_rgb)
        mask = Image.new('L', (width, height))
        mask_data = []

        # Генерация маски градиента по горизонтали
        for y in range(height):
            # Вся строка одинаковая, меняется по X
            row = [int(255 * (x / width)) for x in range(width)]
            mask_data.extend(row)

        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        return base

    def _draw_vector_icon(self, draw: ImageDraw.ImageDraw, icon_type: str, x: float, y: float, size: int,
                          color: Tuple[int, int, int]):
        """
        Отрисовка векторных иконок программно (без загрузки внешних файлов).
        """
        if icon_type == 'building':  # НКО
            draw.rectangle([x, y + size * 0.3, x + size, y + size], fill=color)
            draw.polygon([x, y + size * 0.3, x + size / 2, y, x + size, y + size * 0.3], fill=color)

        elif icon_type == 'clock':  # Время
            draw.ellipse([x, y, x + size, y + size], outline=color, width=2)
            cx, cy = x + size / 2, y + size / 2
            draw.line([cx, cy, cx, cy - size / 3], fill=color, width=2)
            draw.line([cx, cy, cx + size / 3, cy], fill=color, width=2)

        elif icon_type == 'pin':  # Локация
            cx, cy = x + size / 2, y + size / 3
            r = size / 2.5
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
            draw.polygon([cx, cy + r, cx - r / 2, cy, cx + r / 2, cy], fill=color)
            draw.ellipse([cx - r / 3, cy - r / 3, cx + r / 3, cy + r / 3], fill=(255, 255, 255))

        elif icon_type == 'people':  # Аудитория
            for offset in [0, size / 2]:
                draw.ellipse([x + offset, y, x + size / 3 + offset, y + size / 3], fill=color)
                draw.pieslice([x - size / 6 + offset, y + size / 3, x + size / 2 + offset, y + size], 270, 90,
                              fill=color)

    def _draw_pill(self, img: Image.Image, text: str, icon_type: str, font: ImageFont.FreeTypeFont,
                   x: int, y: int, align: str = 'left') -> int:
        """
        Рисует скругленную плашку ("пилюлю") с текстом и иконкой.
        Возвращает Y-координату нижней границы плашки (для отступов).
        """
        if not text:
            return y

        draw = ImageDraw.Draw(img)
        text_color = (0, 0, 0)
        bg_color = (255, 255, 255)

        padding_x = 25
        padding_y = 12
        icon_size = 35
        icon_padding = 15

        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        full_w = padding_x * 2 + icon_size + icon_padding + text_w
        full_h = padding_y * 2 + text_h + 10

        # Расчет координат X в зависимости от выравнивания
        start_x = x
        if align == 'right':
            start_x = x - full_w

        # Фон
        draw.rounded_rectangle([(start_x, y), (start_x + full_w, y + full_h)], radius=full_h / 2, fill=bg_color)

        # Иконка
        icon_x = start_x + padding_x
        icon_y = y + (full_h - icon_size) / 2
        self._draw_vector_icon(draw, icon_type, icon_x, icon_y, icon_size, text_color)

        # Текст (центрирование по вертикали)
        text_x = icon_x + icon_size + icon_padding
        text_y = y + (full_h - text_h) / 2 - 4
        draw.text((text_x, text_y), text, font=font, fill=text_color)

        return y + full_h + 20  # Возвращаем Y + отступ

    async def _render_telegram_card(self, data: CardData) -> bytes:
        """
        Реализация генерации карточки (формат A4 Vertical).
        """
        # 1. Настройки холста (A4 Vertical approx: 1240x1754 px)
        W, H = 1240, 1754

        # Цвета для градиента (Маджента -> Персиковый)
        color_magenta = (225, 70, 220)
        color_peach = (255, 220, 160)

        # Получаем шрифты через кэш класса
        font_title = self._get_font(90, bold=True)
        font_pill = self._get_font(32, bold=False)

        # Создаем базовый холст
        img = Image.new('RGB', (W, H), (255, 255, 255))

        # 2. Обработка изображения (Верхние 60%)
        split_y = int(H * 0.60)

        try:
            if data.image:
                user_img = Image.open(io.BytesIO(data.image)).convert('RGB')
                # Smart crop / Resize
                user_img = ImageOps.fit(user_img, (W, split_y), method=Image.Resampling.LANCZOS)
                img.paste(user_img, (0, 0))
            else:
                raise ValueError("Нет данных изображения")
        except Exception as e:
            logger.error(f"Ошибка обработки изображения: {e}")
            # Зеленый фон-заглушка
            draw_ph = ImageDraw.Draw(img)
            draw_ph.rectangle([(0, 0), (W, split_y)], fill=(0, 255, 0))
            draw_ph.text((W / 2 - 150, split_y / 2), "NO IMAGE", font=font_title, fill=(255, 255, 255))

        # 3. Нижний горизонтальный градиент
        grad_h = H - split_y
        gradient = self._create_horizontal_gradient(W, grad_h, color_magenta, color_peach)
        img.paste(gradient, (0, split_y))

        draw = ImageDraw.Draw(img)

        # 4. Верхние "плашки" (НКО и Дата)
        margin = 50
        top_pill_y = 50

        # Слева: НКО
        if data.ngo_data and data.ngo_data.name:
            self._draw_pill(img, f"НКО «{data.ngo_data.name}»", 'building', font_pill, x=margin, y=top_pill_y,
                            align='left')

        # Справа: Дата и время (из EventData)
        if data.event_data and data.event_data.timestamp:
            self._draw_pill(img, data.event_data.timestamp, 'clock', font_pill, x=W - margin, y=top_pill_y,
                            align='right')

        # 5. Основной контент (Нижняя часть)
        content_y = split_y + 80
        left_margin = 60

        # Заголовок (UPPERCASE, с переносом)
        if data.title:
            title_text = data.title.upper()
            # Используем встроенный textwrap, так как ширина шрифта переменная
            # Подбираем width (кол-во символов) эмпирически для размера шрифта 90
            lines = textwrap.wrap(title_text, width=16)

            for line in lines:
                draw.text((left_margin, content_y), line, font=font_title, fill=(255, 255, 255))
                bbox = font_title.getbbox(line)
                content_y += (bbox[3] - bbox[1]) + 20

        content_y += 30  # Отступ перед нижними плашками

        # Нижние плашки (Локация и Аудитория)
        if data.event_data:
            # Локация
            if data.event_data.location:
                content_y = self._draw_pill(img, data.event_data.location, 'pin', font_pill, x=left_margin, y=content_y,
                                            align='left')

            # Аудитория
            if data.event_data.audience:
                text_aud = f"Для: {data.event_data.audience}"
                self._draw_pill(img, text_aud, 'people', font_pill, x=left_margin, y=content_y, align='left')

        # 6. Сохранение в байты
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=95)
        return output.getvalue()

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

            logger.info(f"Генерация карточки PIL.")

            # FIXME: размер захарддкожен
            width = 1080
            height = 1528

            if parameters.template == CardTemplate.TELEGRAM:
                return await self._render_telegram_card(
                    data
                )

            # Создание основного изображения
            img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # 1. ФОН - Градиент или фоновое изображение
            gradient_bg = self._create_gradient_background(
                width, height,
                '#667eea',
                '#764ba2',
            )

            # Наложение фонового изображения на градиент
            img.paste(gradient_bg)

            # Обработка фонового изображения из bytes
            background_img = Image.open(io.BytesIO(data.image))

            # Проверка формата и конверсия в RGBA если нужно
            if background_img.mode != 'RGBA':
                background_img = background_img.convert('RGBA')

            # Изменение размера фонового изображения под размеры карточки
            background_img = background_img.resize((width, height), Image.Resampling.LANCZOS)

            # Наложение фонового изображения
            img.paste(background_img, (0, 0), background_img)

            logger.info(f"Фоновое изображение наложено: {background_img.size}")


            # Создание темного оверлея для читаемости текста (40% opacity)
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 102))
            img = Image.alpha_composite(img, overlay)

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
            if data.title:
                title_font = self._get_font(48, bold=True)
                title_lines = self._wrap_text(data.title, title_font, content_width)
                title_color = self._hex_to_rgb('#667eea')

                self._draw_multiline_text(
                    draw, title_lines,
                    (content_x, current_y),
                    title_font, title_color
                )

                bbox = title_font.getbbox("Ag")
                title_height = (title_lines.count('\n') + 1) * (bbox[3] - bbox[1] + 10)
                current_y += title_height + 15

            # # 5. ОСНОВНОЙ КОНТЕНТ с поддержкой Markdown
            # if template_data.get('content'):
            #     content_font = self._get_font(24)
            #     content_lines = self._format_markdown_text(template_data['content'], content_font, content_width)
            #     content_color = self._hex_to_rgb(template_data['text_color'])
            #
            #     self._draw_formatted_multiline_text(
            #         draw, content_lines,
            #         (content_x, current_y),
            #         content_font, content_color
            #     )
            #
            #     content_height = len(content_lines) * (content_font.getbbox("Ag")[3] - content_font.getbbox("Ag")[1] + 8)
            #     current_y += content_height + 35


            # 8. FOOTER
            footer_font = self._get_font(20)
            footer_color = self._hex_to_rgb('#667eea')
            footer_text = data.ngo_data.name


            footer_lines = self._wrap_text(footer_text, footer_font, content_width)

            # Позиция футера - внизу карточки
            bbox = footer_font.getbbox("Ag")
            footer_height = (footer_lines.count('\n') + 1) * (bbox[3] - bbox[1] + 4)
            footer_y = round((card_y + card_height - footer_height - 15))

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
            logger.error(f"Ошибка генерации PIL-карточки': {e}")
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
