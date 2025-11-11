import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove
from config import config
from bot.states import ContentGeneration

import json
import io

from bot.utils import get_caption_for_card_type, get_color_by_goal, get_secondary_color_by_goal, get_template_by_goal, get_title_by_goal
from services.card_generation import card_generator
from services.gpt import YandexGPT

logger = logging.getLogger(__name__)

router = Router()

def get_goal_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора цели"""
    kb = [
        [KeyboardButton(text="🎯 Привлечь волонтеров")],
        [KeyboardButton(text="💰 Найти спонсоров/доноров")],
        [KeyboardButton(text="📢 Рассказать о мероприятии")],
        [KeyboardButton(text="❤️ Повысить осведомленность о проблеме")],
        [KeyboardButton(text="🤝 Укрепить отношения со сторонниками")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def get_audience_keyboard(selected: list = None) -> ReplyKeyboardMarkup:
    """Клавиатура для выбора аудитории"""
    if selected is None:
        selected = []
    
    kb = [
        [KeyboardButton(text="👨‍🎓 Молодежь (14-25 лет)")],
        [KeyboardButton(text="👨‍👩‍👧‍👦 Семьи с детьми")],
        [KeyboardButton(text="💼 Работающие взрослые (25-45 лет)")],
        [KeyboardButton(text="👴 Люди старшего возраста (45+)")],
        [KeyboardButton(text="🏢 Бизнес/организации")],
        [KeyboardButton(text="✅ Готово")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=False)

def get_platform_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора платформы"""
    kb = [
        [KeyboardButton(text="📱 ВКонтакте (для молодежи)")],
        [KeyboardButton(text="💬 Telegram (для взрослых/бизнеса)")],
        [KeyboardButton(text="📸 Instagram (визуальный контент)")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def get_format_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора формата контента"""
    kb = [
        [KeyboardButton(text="📝 Информационный пост (70% контента)")],
        [KeyboardButton(text="🎭 Развлекательный/эмоциональный пост (20%)")],
        [KeyboardButton(text="💬 Пост для вовлечения аудитории (10%)")],
        [KeyboardButton(text="📅 Напоминание о мероприятии")],
        [KeyboardButton(text="✅ Готово")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=False)

def get_volume_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора объема"""
    kb = [
        [KeyboardButton(text="📱 Короткий пост (1-3 предложения + карточка)")],
        [KeyboardButton(text="📝 Средний пост (3-5 предложений + 2-3 карточки)")],
        [KeyboardButton(text="📖 Развернутый пост (5+ предложений + 4-5 карточек)")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def get_yes_no_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура Да/Нет"""
    kb = [
        [KeyboardButton(text="✅ Да")],
        [KeyboardButton(text="❌ Нет")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

@router.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Я — ContentHelper, ваш AI-ассистент для создания контента в НКО.\n\n"
        "Я помогу вам создать профессиональные посты и карточки для соцсетей всего за несколько минут!\n\n"
        "Какова основная цель вашего поста?",
        reply_markup=get_goal_keyboard()
    )
    await state.set_state(ContentGeneration.waiting_for_goal)

@router.message(ContentGeneration.waiting_for_goal, F.text)
async def goal_handler(message: Message, state: FSMContext):
    goal = message.text
    await state.update_data(goal=goal)
    
    await message.answer(
        "👥 Кто ваша целевая аудитория? (можно выбрать несколько вариантов, нажмите ✅ Готово когда закончите)",
        reply_markup=get_audience_keyboard()
    )
    await state.set_state(ContentGeneration.waiting_for_audience)

@router.message(ContentGeneration.waiting_for_audience, F.text)
async def audience_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    audience_list = data.get('audience', [])
    
    if message.text == "✅ Готово":
        if not audience_list:
            await message.answer("Пожалуйста, выберите хотя бы одну аудиторию.")
            return
        
        await message.answer(
            "📱 На какой платформе будет публиковаться контент?",
            reply_markup=get_platform_keyboard()
        )
        await state.set_state(ContentGeneration.waiting_for_platform)
        return
    
    # Добавляем или удаляем аудиторию
    if message.text in audience_list:
        audience_list.remove(message.text)
    else:
        audience_list.append(message.text)
    
    await state.update_data(audience=audience_list)
    
    # Показываем текущий выбор
    selected = "\n".join([f"✓ {a}" for a in audience_list]) if audience_list else "Пока ничего не выбрано"
    await message.answer(
        f"Текущий выбор аудитории:\n{selected}\n\n"
        "Выберите еще или нажмите ✅ Готово",
        reply_markup=get_audience_keyboard(audience_list)
    )

@router.message(ContentGeneration.waiting_for_platform, F.text)
async def platform_handler(message: Message, state: FSMContext):
    platform = message.text
    await state.update_data(platform=platform)
    
    await message.answer(
        "📊 Какой формат контента вам нужен? (можно выбрать несколько)",
        reply_markup=get_format_keyboard()
    )
    await state.set_state(ContentGeneration.waiting_for_format)

@router.message(ContentGeneration.waiting_for_format, F.text)
async def format_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    format_list = data.get('format', [])
    
    if message.text == "✅ Готово":
        if not format_list:
            await message.answer("Пожалуйста, выберите хотя бы один формат контента.")
            return
        
        await message.answer(
            "🎉 Есть ли у вас конкретное мероприятие для продвижения?",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(ContentGeneration.waiting_for_has_event)
        return
    
    # Добавляем или удаляем формат
    if message.text in format_list:
        format_list.remove(message.text)
    else:
        format_list.append(message.text)
    
    await state.update_data(format=format_list)
    
    # Показываем текущий выбор
    selected = "\n".join([f"✓ {f}" for f in format_list]) if format_list else "Пока ничего не выбрано"
    await message.answer(
        f"Текущий выбор форматов:\n{selected}\n\n"
        "Выберите еще или нажмите ✅ Готово",
        reply_markup=get_format_keyboard()
    )

@router.message(ContentGeneration.waiting_for_has_event, F.text.in_(["✅ Да", "❌ Нет"]))
async def has_event_handler(message: Message, state: FSMContext):
    has_event = message.text == "✅ Да"
    await state.update_data(has_event=has_event)
    
    if has_event:
        await message.answer(
            "📅 Когда и где состоится мероприятие?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Пропустить")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        await state.set_state(ContentGeneration.waiting_for_event_details)
    else:
        await message.answer(
            "📏 Какой объем контента вам нужен?",
            reply_markup=get_volume_keyboard()
        )
        await state.set_state(ContentGeneration.waiting_for_volume)

@router.message(ContentGeneration.waiting_for_event_details, F.text)
async def event_details_handler(message: Message, state: FSMContext):
    event_details = message.text if message.text != "Пропустить" else ""
    await state.update_data(event_details=event_details)
    
    await message.answer(
        "📏 Какой объем контента вам нужен?",
        reply_markup=get_volume_keyboard()
    )
    await state.set_state(ContentGeneration.waiting_for_volume)

@router.message(ContentGeneration.waiting_for_volume, F.text)
async def volume_handler(message: Message, state: FSMContext):
    volume = message.text
    await state.update_data(volume=volume)
    
    await message.answer(
        "✏️ Теперь расскажите подробнее, о чем вы хотите рассказать в посте. "
        "Это поможет мне создать максимально релевантный контент.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пример: Нужны волонтеры для помощи детям с подготовкой к школе")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    await state.set_state(ContentGeneration.waiting_for_user_text)


@router.message(ContentGeneration.waiting_for_user_text, F.text)
async def user_text_handler(message: Message, state: FSMContext):
    user_text = message.text
    await state.update_data(user_text=user_text)
    
    data = await state.get_data()
    goal = data.get('goal', '')
    
    await message.answer("🧠 Генерирую контент с помощью YandexGPT...", reply_markup=ReplyKeyboardRemove())
    
    try:
        yandexgpt_client = YandexGPT()
        generated_post = await yandexgpt_client.generate_content(data, user_text)
        await state.update_data(generated_post=generated_post)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации контента: {e}")
        await message.answer(
            f"❌ Ошибка при работе с YandexGPT:\n{str(e)}\n\n",
            parse_mode=None
        )
        raise
    
    # Отображаем сгенерированный пост
    await message.answer(
        f"✅ Ваш сгенерированный контент:\n\n{generated_post}",
        parse_mode=None
    )
    
    # Продолжаем генерацию карточек (этот код остается без изменений)
    await message.answer("🎨 Создаю информационные карточки...")

    # Продолжаем генерацию карточек с использованием вашего CardGenerator
    await message.answer("🎨 Создаю информационные карточки...")
    
    try:
        # Подготавливаем данные для шаблона
        template_data = {
            'title': get_title_by_goal(goal),
            'subtitle': f"Для {', '.join(data.get('audience', ['наших подопечных']))}",
            'content': generated_post[:250] + '...' if len(generated_post) > 250 else generated_post,
            'org_name': 'Ваша НКО',
            'contact_info': 'тел: +7 (XXX) XXX-XX-XX',
            'primary_color': get_color_by_goal(goal),
            'secondary_color': get_secondary_color_by_goal(goal),
            'text_color': '#333',
            'background_color': '#f5f7fa'
        }
        
        # Определяем тип шаблона на основе цели
        template_name = get_template_by_goal(goal)
        
        # Используем ваш CardGenerator для генерации карточек
        cards = await card_generator.generate_multiple_cards(
            template_name=template_name,
            data=template_data,
            platform=platform
        )
        
        if not cards:
            raise Exception("Не удалось сгенерировать карточки")
        
        # Отправляем карточки пользователю
        await message.answer("🎨 Вот ваши карточки для соцсетей:")
        
        for card_type, image_bytes in cards.items():
            caption = get_caption_for_card_type(card_type, platform)
            await message.answer_photo(
                photo=io.BytesIO(image_bytes),
                caption=caption
            )
        
        # Кнопки действий
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Создать еще", callback_data="create_again")],
            [InlineKeyboardButton(text="💡 Советы по продвижению", callback_data="get_tips")],
            [InlineKeyboardButton(text="📤 Экспортировать все", callback_data="export_all")]
        ])
        
        await message.answer(
            "✨ Все карточки готовы к публикации!\n"
            "Что хотите сделать дальше?",
            reply_markup=kb
        )
        
        await state.set_state(ContentGeneration.waiting_for_confirmation)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации карточек: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании карточек.\n\n"
            "Попробуйте:\n"
            "• Перезапустить бота (/start)\n"
            "• Выбрать другую платформу\n"
            "• Упростить описание",
            parse_mode=None
        )


@router.callback_query(F.data == "create_again")
async def create_again_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)

@router.callback_query(F.data == "download_all")
async def download_all_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Функция скачивания будет доступна в продакшен-версии", show_alert=True)

@router.callback_query(F.data == "get_tips")
async def get_tips_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    platform = data.get('platform', '')
    audience = ', '.join(data.get('audience', []))
    goal = data.get('goal', '')
    
    tips = {
        "📱 ВКонтакте (для молодежи)": (
            "💡 Советы для ВКонтакте:\n\n"
            "• Публикуйте в 18:00-21:00, когда аудитория наиболее активна\n"
            "• Используйте 3-5 релевантных хештегов\n"
            "• Добавляйте эмодзи в начале каждого абзаца\n"
            "• Публикуйте 3-4 раза в неделю для поддержания интереса\n"
            "• Отвечайте на комментарии в течение 1-2 часов"
        ),
        "💬 Telegram (для взрослых/бизнеса)": (
            "💡 Советы для Telegram:\n\n"
            "• Публикуйте в рабочие дни с 10:00 до 16:00\n"
            "• Используйте форматирование (**жирный**, _курсив_)\n"
            "• Добавляйте разделители --- между секциями\n"
            "• Публикуйте 1-2 раза в неделю, чтобы не спамить\n"
            "• Используйте кнопки для призывов к действию"
        ),
        "📸 Instagram (визуальный контент)": (
            "💡 Советы для Instagram:\n\n"
            "• Публикуйте сторис ежедневно для поддержания активности\n"
            "• Основные посты - 3-4 раза в неделю\n"
            "• Используйте актуальные музыкальные треки в сторис\n"
            "• Добавляйте геолокацию для локального охвата\n"
            "• Отвечайте на DM в течение 24 часов"
        )
    }
    
    tip_text = tips.get(platform, (
        "💡 Общие советы по продвижению:\n\n"
        "• Публикуйте регулярно, чтобы аудитория не забывала о вас\n"
        "• Используйте смесь информационного и развлекательного контента\n"
        "• Задавайте вопросы в постах для повышения вовлеченности\n"
        "• Анализируйте статистику и адаптируйте стратегию\n"
        "• Сотрудничайте с другими НКО для взаимного продвижения"
    ))
    
    await callback.message.answer(tip_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="create_again")]
    ]))

@router.message(F.text)
async def fallback_handler(message: Message):
    await message.answer(
        "Я не понимаю эту команду. Используйте /start для начала работы или выберите вариант из меню.",
        reply_markup=get_goal_keyboard() if message.text == "/start" else None
    )