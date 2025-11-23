import logging
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps


logger = logging.getLogger(__name__)

def create_gradient(width, height, color1, color2):
    """Создает горизонтальный градиент."""
    base = Image.new('RGB', (width, height), color1)
    top = Image.new('RGB', (width, height), color2)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        for x in range(width):
            mask_data.append(int(255 * (x / width)))
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def draw_icon(draw, icon_type, x, y, size, color):
    """Рисует схематичные иконки."""
    if icon_type == 'building': # Иконка НКО
        draw.rectangle([x, y + size*0.2, x + size, y + size], fill=color)
        # Окна
        w_size = size * 0.2
        for i in range(2):
            for j in range(2):
                draw.rectangle([x + size*0.2 + i*w_size*1.5, y + size*0.4 + j*w_size*1.5, 
                                x + size*0.2 + i*w_size*1.5 + w_size, y + size*0.4 + j*w_size*1.5 + w_size], fill=(255,255,255))
    
    elif icon_type == 'pin': # Иконка локации
        cx, cy = x + size/2, y + size/3
        r = size/2.5
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)
        draw.polygon([cx, cy+r, cx-r/2, cy, cx+r/2, cy], fill=color) # Ножка
        draw.polygon([cx, y+size, cx-2, cy+r/2, cx+2, cy+r/2], fill=color) # Острие
        draw.ellipse([cx-r/3, cy-r/3, cx+r/3, cy+r/3], fill=(255,255,255)) # Точка внутри

    elif icon_type == 'people': # Иконка аудитории
        # Человек 1
        draw.ellipse([x, y, x + size/3, y + size/3], fill=color) # Голова
        draw.pieslice([x - size/6, y + size/3, x + size/2, y + size], 270, 90, fill=color)
        # Человек 2
        draw.ellipse([x + size/2, y, x + size/2 + size/3, y + size/3], fill=color)
        draw.pieslice([x + size/3, y + size/3, x + size, y + size], 270, 90, fill=color)


def load_font(font_names, size):
    """Перебирает список шрифтов и загружает первый найденный."""
    # Стандартные пути к шрифтам в Linux, где PIL может их найти
    font_dirs = [
        "/usr/share/fonts",
        "/usr/share/fonts/truetype",
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/truetype/liberation",
        "/usr/share/fonts/truetype/freefont"
    ]
    
    for name in font_names:
        try:
            # 1. Пробуем загрузить просто по имени (если система настроена)
            return ImageFont.truetype(name, size)
        except OSError:
            # 2. Если не вышло, пробуем искать файл вручную в папках
            for folder in font_dirs:
                path = os.path.join(folder, name)
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
                # Иногда файлы лежат во вложенных папках, но PIL это обычно сам не делает
                
    # Если ничего не нашли, возвращаем дефолтный (уродливый, но работает)
    logger.warning(f"Внимание: Шрифты {font_names} не найдены. Используется стандартный.")
    return ImageFont.load_default()



def draw_pill(img, x, y, text, icon_type, font, text_color=(0,0,0), bg_color=(255,255,255)):
    """Рисует скругленную плашку с иконкой и текстом."""
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
    full_h = padding_y * 2 + text_h + 10 # +10 для запаса на высоту шрифта
    
    # Рисуем скругленный прямоугольник (фон)
    shape = [(x, y), (x + full_w, y + full_h)]
    draw.rounded_rectangle(shape, radius=full_h/2, fill=bg_color)
    
    # Рисуем иконку
    icon_x = x + padding_x
    icon_y = y + (full_h - icon_size) / 2
    draw_icon(draw, icon_type, icon_x, icon_y, icon_size, text_color)
    
    # Рисуем текст
    text_x = icon_x + icon_size + icon_padding
    # Центруем текст по вертикали
    text_y = y + (full_h - text_h) / 2 - 5 # -5 небольшая коррекция базовой линии
    draw.text((text_x, text_y), text, font=font, fill=text_color)
    
    return y + full_h + 15 # Возвращаем Y координату для следующего элемента (+ отступ)

def generate_card(
    ngo_name,
    event_datetime,
    location,
    audience,
    title,
    body_text,
    image_path,
    output_path,
    width=1080,
    height=1440,
):
    logging.info("Генерирую карточку...")
    
    # Цвета градиента
    grad_color_1 = (225, 70, 220)  # Маджента/Розовый (слева)
    grad_color_2 = (255, 220, 160) # Персиковый/Желтый (справа)
    
    # Загрузка шрифтов 
    try:
        # Списки приоритетов: Сначала Arial, потом аналоги Linux
        fonts_bold = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "FreeSansBold.ttf"]
        fonts_reg = ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "FreeSans.ttf"]

        font_title = load_font(fonts_bold, 80) # Заголовок
        font_body = load_font(fonts_reg, 40)   # Текст
        font_pill = load_font(fonts_reg, 30)   # Плашки
        font_npo = load_font(fonts_bold, 30)   # НКО
    except:
        # Фолбэк, если нет Arial
        font_title = ImageFont.load_default()
        font_body = font_pill = font_npo = font_title

    # Создаем базу
    img = Image.new('RGB', (width, height), (255, 255, 255))
    
    # --- 2. ВЕРХНЯЯ ЧАСТЬ (КАРТИНКА ПОЛЬЗОВАТЕЛЯ) ---
    # Картинка занимает примерно 65% высоты
    split_y = int(height * 0.65)
    
    try:
        user_img = Image.open(image_path).convert('RGB')
        # Масштабируем картинку (cover), чтобы заполнить верх
        user_img = ImageOps.fit(user_img, (width, split_y), method=Image.Resampling.LANCZOS)
        img.paste(user_img, (0, 0))
    except Exception as e:
        logger.error(f"Ошибка картинки при генерации карточки: {e}.")
        raise e

    # --- 3. НИЖНЯЯ ЧАСТЬ (ГРАДИЕНТ И ТЕКСТ) ---
    # Генерируем градиент для нижней части
    gradient_h = height - split_y
    gradient_img = create_gradient(width, gradient_h, grad_color_1, grad_color_2)
    img.paste(gradient_img, (0, split_y))
    
    draw = ImageDraw.Draw(img)
    
    # Координаты контента в нижней части
    content_margin_left = 60
    current_y = split_y + 60 # Отступ сверху от границы градиента
    
    # А) ЗАГОЛОВОК (Белый, жирный, капсом)
    # Разбиваем заголовок, если он длинный
    import textwrap
    title_lines = textwrap.wrap(title.upper(), width=18) # Подбираем width под размер шрифта
    
    for line in title_lines:
        draw.text((content_margin_left, current_y), line, font=font_title, fill=(255, 255, 255))
        bbox = font_title.getbbox(line)
        current_y += (bbox[3] - bbox[1]) + 15 # Сдвигаем Y вниз
        
    # Б) ОСНОВНОЙ ТЕКСТ (body_text)
    # Если есть текст, добавляем его чуть ниже заголовка
    if body_text:
        current_y += 20 # Доп отступ
        body_lines = textwrap.wrap(body_text, width=45)
        for line in body_lines:
            draw.text((content_margin_left, current_y), line, font=font_body, fill=(255, 255, 255))
            bbox = font_body.getbbox(line)
            current_y += (bbox[3] - bbox[1]) + 10
            
    current_y += 30 # Отступ перед плашками
    
    # В) ПЛАШКИ С ДАННЫМИ (PILLS)
    # 1. Локация + Дата (объединим их в одну строку или две плашки, если длинно)
    # Формируем строку адреса
    loc_text = f"{location}"
    # Рисуем плашку
    next_y = draw_pill(img, content_margin_left, current_y, loc_text, 'pin', font_pill)
    
    # Если нужно, добавляем плашку даты отдельно (или вместе)
    # На референсе 2 строки плашек. Сделаем дату отдельной строкой, если она есть.
    # Но в задании "Дата и время". Добавим отдельную плашку для даты, чтобы использовать все входные данные.
    # Либо добавим дату в текст плашки локации, если хотим строгий шаблон.
    # Сделаем отдельной плашкой ДЛЯ АУДИТОРИИ (как на референсе "Для семей..."), 
    # а дату добавим текстом выше или новой плашкой. 
    # Добавим плашку даты:
    current_y = next_y
    date_text = f"{event_datetime}"
    # Используем иконку pin повторно или можно сделать иконку часов, но пока пусть будет текст
    # Чтобы было красиво, просто выведем "Дата: ..."
    # Но лучше соблюсти стиль. Рисуем плашку аудитории.
    
    audience_text = f"Для: {audience}"
    next_y = draw_pill(img, content_margin_left, current_y, audience_text, 'people', font_pill)
    
    # Плашку даты нарисуем справа или под, если есть место. 
    # Вставим дату прямо перед локацией для логики, или после.
    # Для простоты добавим дату в заголовок плашки локации? Нет.
    # Нарисуем "Date Pill" между текстом и локацией, если осталось место, или самой нижней.
    # Давайте добавим дату ПЕРЕД локацией, так логичнее.
    
    # --- 4. ВЕРХНЯЯ ПЛАШКА (НКО) ---
    # Рисуется поверх картинки в левом верхнем углу
    npo_text = f"НКО «{ngo_name}»"
    draw_pill(img, 40, 40, npo_text, 'building', font_npo)
    
    # Сохранение
    img.save(output_path)
    logging.info(f"Генерация карточки завершена. Сохранено в {output_path}")
