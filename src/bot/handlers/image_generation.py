import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.input_file import BufferedInputFile
from aiogram.enums.parse_mode import ParseMode

from bot import dispatcher, bot
from bot.states import ImageGeneration, ContentGeneration
from services.image_generation import ImageGenerationService
from services.ngo_service import NGOService
from services.text_generation import TextGenerationService

BACK_TO_MAIN_MENU_CALLBACK_DATA = "back_to_main"

image_generation_router = Router(name="image_generation")

logger = logging.getLogger(__name__)


GENERATE_IMAGES_CALLBACK_DATA = "generate_images"
BACK_TO_IMAGE_MENU_CALLBACK_DATA = "back_to_image_menu"


CARD_PHOTO_CHOICE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI сгенерирует фото", callback_data="card_photo_ai")],
        [InlineKeyboardButton(text="📎 Загрузить своё фото", callback_data="card_photo_upload")],
        [InlineKeyboardButton(text="🚫 Без фото", callback_data="card_photo_none")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_confirmation")]
    ]
)


async def complete_generation_handler(message: Message, state: FSMContext) -> None:
    """
    Универсальная функция завершения генерации текстового контента.

    Функция обрабатывает завершающий этап генерации контента, включая:
    - Получение данных пользователя из состояния FSM
    - Генерацию текстового контента с помощью YandexGPT
    - Обработку изображений (ИИ генерация, загрузка пользователя или без фото)
    - Переход к генерации карточек или запрос выбора фото для карточек

    Args:
        message (Message): Входящее сообщение от пользователя
        state (FSMContext): Контекст состояния конечного автомата

    Raises:
        Exception: При ошибке генерации текстового контента
        Exception: При ошибке генерации изображения
    """
    # Получаем данные из состояния
    data = await state.get_data()
    user_text = data.get("user_text", "")

    # Извлекаем параметры генерации
    goal = data.get("goal", "🎯 Рассказать о мероприятии")
    platform = data.get("platform", "📱 ВКонтакте (для молодежи)")

    # Получаем информацию об НКО из базы данных
    ngo_service: NGOService = dispatcher["ngo_service"]
    user_id = message.from_user.id
    ngo_data = ngo_service.get_ngo_data_by_user_id(user_id)

    # Обновляем данные пользователя информацией из БД
    if ngo_data:
        data.update(ngo_data)

    # Устанавливаем значения по умолчанию
    ngo_name = ngo_data.get("ngo_name", "Ваша НКО") if ngo_data else "Ваша НКО"
    ngo_contact = ngo_data.get("ngo_contact", "тел: +7 (XXX) XXX-XX-XX") if ngo_data else "тел: +7 (XXX) XXX-XX-XX"

    generated_post = None

    # Уведомляем пользователя о начале генерации
    await message.answer(
        "🧠 Генерирую контент...",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Генерируем текстовый контент
    try:
        text_generation_service: TextGenerationService = dispatcher["text_content_generation_service"]
        generated_post = await text_generation_service.generate_text(data, user_text)
        await state.update_data(generated_post=generated_post)
    except Exception as error:
        logger.exception("Ошибка при генерации текста: %s", error)
        await message.answer(
            "⚠️ Не удалось получить ответ.",
            reply_markup=ReplyKeyboardRemove(),
        )
        raise error

    # Показываем сгенерированный пост пользователю
    await message.answer(
        "✅ Ваш сгенерированный контент:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        generated_post,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
    )

    # Обработка изображения для основного контента
    image_source = data.get("image_source")
    user_image = data.get("user_image")
    image_prompt = data.get("image_prompt")
    generated_image = None

    logger.info(
        f"Обработка изображения: source={image_source}, user_image={'есть' if user_image else 'нет'}, prompt={image_prompt[:50] + '...' if image_prompt and len(image_prompt) > 50 else image_prompt}")

    # Обработка различных источников изображения
    if image_source == "🤖 Сгенерировать ИИ" and image_prompt:
        await message.answer(
            "🎨 Генерирую изображение ИИ...",
            reply_markup=ReplyKeyboardRemove(),
        )
        try:
            image_generation_service = dp.get("image_generation_service")
            if not image_generation_service:
                raise Exception("Сервис генерации изображений не инициализирован")

            # Формируем умный промпт для генерации изображения
            smart_prompt = image_prompt
            if data.get("generation_mode") == "structured":
                event_context = f". Стиль: иллюстрация к событию '{data.get('event_type', '')}' в '{data.get('event_place', '')}' для '{data.get('event_audience', '')}'"
                smart_prompt += event_context
            logger.info(f"Генерируем изображение с промпт: {smart_prompt}")

            generated_image = await image_generation_service.generate_image(
                prompt=smart_prompt,
                width=1024,
                height=768
            )
            logger.info(f"Изображение сгенерировано, размер: {len(generated_image) if generated_image else 0} байт")

            # Сохраняем AI-сгенерированное изображение в состояние
            await state.update_data(ai_generated_image=generated_image)
            await message.answer(
                "✅ Изображение ИИ готово!",
                reply_markup=ReplyKeyboardRemove(),
            )
        except Exception as e:
            logger.exception(f"Ошибка генерации изображения ИИ: {e}")
            await message.answer(
                "⚠️ Не удалось сгенерировать изображение ИИ. Продолжаю с карточками без изображения.",
                reply_markup=ReplyKeyboardRemove(),
            )
    elif image_source == "📎 Загрузить своё" and user_image:
        logger.info(f"Используем пользовательское изображение, размер: {len(user_image)} байт")
        await message.answer(
            "🎨 Использую ваше изображение...",
            reply_markup=ReplyKeyboardRemove(),
        )
        generated_image = user_image
    elif image_source == "🚫 Без фото":
        logger.info("Пользователь выбрал без фото")
        generated_image = None
        await message.answer(
            "✅ Выбрано: Без фото для карточки",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        logger.info("Изображение не будет использовано")

    # Если пользователь уже выбрал генерацию ИИ изображения для общего контента,
    # автоматически используем его для карточки вместо повторного выбора
    if image_source == "🤖 Сгенерировать ИИ":
        logger.info("Пользователь выбрал AI изображение для контента - пропускаем выбор фото для карточки")
        await generate_cards_handler(message, state)
        return

    # Спрашиваем у пользователя выбор фото для карточки
    await message.answer(
        "🖼️ **Выберите источник фото для информационных карточек:**",
        reply_markup=ReplyKeyboardRemove(),
    )

    await message.answer(
        "Какое фото использовать для карточки?",
        reply_markup=CARD_PHOTO_CHOICE_KEYBOARD,
    )
    await state.set_state(ContentGeneration.waiting_for_card_photo_choice)


IMAGE_SOURCE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Сгенерировать ИИ", callback_data="image_source_ai")],
        [InlineKeyboardButton(text="📎 Загрузить своё", callback_data="image_source_upload")],
        [InlineKeyboardButton(text="🚫 Без фото", callback_data="image_source_none")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_platform")]
    ]
)

async def image_source_handler_common(callback: CallbackQuery, state: FSMContext, image_source: str):
    """Общий обработчик для выбора источника изображения."""
    await state.update_data(image_source=image_source)

    if image_source == "🤖 Сгенерировать ИИ":
        # Переходим к генерации ИИ
        await callback.message.answer(
            "🎨 **Опишите желаемую картинку для карточки**\n"
            "Опишите, как должна выглядеть иллюстрация к вашему посту. "
            "Можете упомянуть стиль, цвета, настроение.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_image_prompt)
    elif image_source == "📎 Загрузить своё":
        await callback.message.answer(
            "📎 **Загрузите изображение**\n"
            "Пришлите фотографию или изображение, которое будет использовано в карточке. "
            "Поддерживаемые форматы: JPEG, PNG.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_user_image)
    else:  # "🚫 Без фото"
        await callback.message.answer(
            "✅ **Выбрано: Без фото**\n"
            "🎨 Создаем контент без изображения...",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Переходим к генерации контента без фото
        await complete_generation_handler(callback.message, state)


DESCRIBE_IMAGE_CALLBACK_DATA = "describe_image"

IMAGE_GENERATION_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Описать изображение", callback_data=DESCRIBE_IMAGE_CALLBACK_DATA)],
        # FIXME: Из созданного контента не работает
        [InlineKeyboardButton(text="🎭 Из созданного контента", callback_data="image_from_content")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_MAIN_MENU_CALLBACK_DATA)]
    ]
)


# FIXME: Обработчик используется
@image_generation_router.callback_query(F.data == GENERATE_IMAGES_CALLBACK_DATA)
async def generate_images_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик генерации изображений."""
    await callback.answer()
    await state.clear()

    await callback.message.answer(
        "🎨 Генерация изображений\n\n"
        "Я могу помочь вам сгенерировать картинки для ваших постов!\n\n"
        "**Какое изображение вы хотите сгенерировать?**\n\n"
        "Опишите тему и стиль изображения, например:\n"
        "• Портрет волонтера в солнечном парке\n"
        "• Группа детей за благотворительным мероприятием\n"
        "• Иконка для сбора средств на помощь животным\n"
        "• Иллюстрация для поста о защите окружающей среды\n\n"
        "Или нажмите кнопку ниже для генерации на основе уже созданного контента.",
        reply_markup=IMAGE_GENERATION_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )



@image_generation_router.callback_query(F.data == BACK_TO_IMAGE_MENU_CALLBACK_DATA)
async def back_to_image_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню генерации изображений."""
    await callback.answer()
    await state.clear()

    await callback.message.answer(
        "🎨 Генерация изображений\n\n"
        "Выберите вариант генерации:",
        reply_markup=IMAGE_GENERATION_KEYBOARD,
    )


@image_generation_router.callback_query(F.data == DESCRIBE_IMAGE_CALLBACK_DATA)
async def describe_image_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик описания изображения."""
    await callback.answer()
    await state.clear()
    await state.set_state(ContentGeneration.waiting_for_image_description)

    await callback.message.answer(
        "🎨 **Опишите изображение**\n\n"
        "Расскажите, какое изображение вы хотите получить. Будьте максимально подробны:\n\n"
        "• Какие объекты/люди должны быть на изображении?\n"
        "• Какое настроение/атмосфера?\n"
        "• Цветовая гамма? (яркая, пастельная, монохромная...)\n"
        "• Стиль изображения? (реалистичный, иллюстрация, минимализм...)\n\n"
        "_Пример: «Группа улыбающихся детей играет в парке на ярком солнце, теплые цвета, реалистичный стиль»_",
        parse_mode=ParseMode.MARKDOWN,
    )


# Размеры изображений
IMAGE_SIZES = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📱 Квадрат (1024x1024)")], # , (1024, 1024)
        [InlineKeyboardButton(text="📺 Горизонтальное (1200x630)")], # , (1200, 630),
        [InlineKeyboardButton(text="📱 Вертикальное (630x1200)")], # : (630, 1200),
    ]
)





@image_generation_router.message(ImageGeneration.waiting_for_prompt, F.text)
async def prompt_handler(message: Message, state: FSMContext):
    """Обработчик текстового описания изображения."""
    
    prompt = message.text.strip()
    
    if not prompt:
        await message.answer(
            "⚠️ Пожалуйста, опишите изображение, которое вы хотите получить."
        )
        return
    
    await state.update_data(prompt=prompt)
    await state.set_state(ImageGeneration.waiting_for_size)
    
    await message.answer(
        "📐 Выберите размер изображения:",
        reply_markup=IMAGE_SIZES,
    )



# FIXME: переделай на коллбэк или вырежи
@image_generation_router.message(ImageGeneration.waiting_for_size, F.text)
async def size_handler(message: Message, state: FSMContext):
    """Обработчик выбора размера изображения."""
    size_option = message.text
    size = IMAGE_SIZES.get(size_option)
    
    if not size:
        await message.answer(
            "⚠️ Пожалуйста, выберите размер из предложенных вариантов.",
            reply_markup=IMAGE_SIZES,
        )
        return
    
    width, height = size
    data = await state.get_data()
    prompt = data.get("prompt", "")
    
    await message.answer(
        f"🎨 Генерирую изображение... (может занять несколько минут)\n\n"
        f"📝 Описание: {prompt}\n"
        f"📐 Размер: {width}x{height}",
        reply_markup=ReplyKeyboardRemove(),
    )
    from bot.handlers.start import BACK_TO_START_KEYBOARD

    try:
        # Получаем сервис генерации изображений
        image_service: ImageGenerationService = dispatcher["image_generation_service"]
        
        # Генерируем изображение
        image_bytes = await image_service.generate_image(
            prompt=prompt,
            width=width,
            height=height,
        )
        
        # Отправляем изображение пользователю
        await message.answer_photo(
            photo=BufferedInputFile(image_bytes, "generated_image.png"),
            caption=f"✅ Изображение готово!\n\n📝 Описание: {prompt}",
            parse_mode=ParseMode.MARKDOWN,
        )

        await message.answer(
            "✨ Изображение успешно сгенерировано!\n\n"
            "Что вы хотите сделать дальше?",
            reply_markup=BACK_TO_START_KEYBOARD,
        )
        
        await state.clear()
        
    except Exception as error:
        logger.exception("Ошибка при генерации изображения: %s", error)
        await message.answer(
            "❌ К сожалению, не удалось сгенерировать изображение.\n"
            f"Ошибка: {str(error)}\n\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=BACK_TO_START_KEYBOARD,
        )
        await state.clear()


@image_generation_router.callback_query(F.data == "image_source_ai")
async def image_source_ai_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора ИИ для генерации изображения."""
    await callback.answer()
    await image_source_handler_common(callback, state, "🤖 Сгенерировать ИИ")


@image_generation_router.callback_query(F.data == "image_source_upload")
async def image_source_upload_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора загрузки своего изображения."""
    await callback.answer()
    await image_source_handler_common(callback, state, "📎 Загрузить своё")


@image_generation_router.callback_query(F.data == "image_source_none")
async def image_source_none_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора без фото."""
    await callback.answer()
    await image_source_handler_common(callback, state, "🚫 Без фото")


async def platform_handler_common(callback: CallbackQuery, state: FSMContext, platform_name: str):
    """Общий обработчик для всех платформ - переход к выбору источника изображения."""
    await state.update_data(platform=platform_name)

    # Новый шаг: выбор источника изображения перед генерацией карточек
    await callback.message.answer(
        "🖼️ **Выберите источник тематической картинки для карточки:**",
        reply_markup=IMAGE_SOURCE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_image_source)


@image_generation_router.message(ContentGeneration.waiting_for_image_prompt, F.text)
async def image_prompt_handler(message: Message, state: FSMContext):
    """Обработчик для описания изображения ИИ."""
    image_prompt = message.text.strip()
    if not image_prompt:
        await message.answer(
            "Пожалуйста, опишите желаемое изображение.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(image_prompt=image_prompt)

    # Переходим к генерации контента
    await complete_generation_handler(message, state)


@image_generation_router.message(ContentGeneration.waiting_for_user_image, F.photo)
async def user_image_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского изображения."""
    if not message.photo:
        await message.answer(
            "Пожалуйста, загрузите изображение (фото).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Получаем наибольшее по размеру фото для лучшего качества
    photo = message.photo[-1]

    # Скачиваем изображение

    try:
        image_file = await bot.download(photo.file_id, destination=None)
        image_bytes = image_file.read()

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке изображения: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


IMAGE_STYLE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Реалистичный", callback_data="image_style_realistic")],
        [InlineKeyboardButton(text="🌈 Иллюстрация", callback_data="image_style_illustration")],
        [InlineKeyboardButton(text="⚪ Минимум", callback_data="image_style_minimal")],
        [InlineKeyboardButton(text="🔷 Абстрактный", callback_data="image_style_abstract")],
        # TODO: Добавь свой вариант
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_IMAGE_MENU_CALLBACK_DATA)]
    ]
)


@image_generation_router.callback_query(F.data == "back_to_style_selection")
async def back_to_style_selection_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору стиля изображения."""
    await callback.answer()

    await callback.message.answer(
        "🎭 **Выберите стиль генерации:**",
        reply_markup=IMAGE_STYLE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_image_style)



@image_generation_router.callback_query(F.data == "image_from_content")
async def image_from_content_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик генерации изображения на основе созданного контента."""
    await callback.answer()

    # Проверяем наличие сгенерированного контента в состоянии
    data = await state.get_data()
    generated_content = data.get("generated_content", "")

    if not generated_content:
        await callback.message.answer(
            "❌ **У вас нет текущего сгенерированного контента**\n\n"
            "Сначала создайте пост, а потом сможете сгенерировать изображение на его основе.",
            reply_markup=IMAGE_GENERATION_KEYBOARD,
        )
        return

    await state.update_data(generation_mode="image_from_content")
    await state.set_state(ContentGeneration.waiting_for_image_style)

    # Показываем превью контента и запрашиваем стиль
    preview = generated_content[:300] + "..." if len(generated_content) > 300 else generated_content

    await callback.message.answer(
        "🎭 **Генерация изображения на основе вашего контента**\n\n"
        "Превью контента:\n"
        f"```\n{preview}\n```\n\n"
        "**Выберите стиль генерации:**",
        reply_markup=IMAGE_STYLE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )


# === ОБРАБОТЧИКИ ВЫБОРА СТИЛЯ ИЗОБРАЖЕНИЯ ===
@image_generation_router.callback_query(F.data == "image_style_realistic")
async def image_style_realistic_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора реалистичного стиля."""
    await callback.answer()
    await process_image_generation(callback, state, "реалистичный стиль")


@image_generation_router.callback_query(F.data == "image_style_illustration")
async def image_style_illustration_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора иллюстративного стиля."""
    await callback.answer()
    await process_image_generation(callback, state, "иллюстрация в ярком стиле")


@image_generation_router.callback_query(F.data == "image_style_minimal")
async def image_style_minimal_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора минималистичного стиля."""
    await callback.answer()
    await process_image_generation(callback, state, "минималистичный стиль")


@image_generation_router.callback_query(F.data == "image_style_abstract")
async def image_style_abstract_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора абстрактного стиля."""
    await callback.answer()
    await process_image_generation(callback, state, "абстрактная композиция")


IMAGE_SIZE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📱 Квадрат (1024×1024)", callback_data="image_size_1024x1024")],
        [InlineKeyboardButton(text="📺 Горизонтал (1200×630)", callback_data="image_size_1200x630")],
        [InlineKeyboardButton(text="📱 Вертикал (630×1200)", callback_data="image_size_630x1200")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_style_selection")]
    ]
)


async def process_image_generation(callback: CallbackQuery, state: FSMContext, style: str):
    """Обработка генерации изображения."""
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "")

    if generation_mode == "image_from_content":
        # Генерация на основе контента
        generated_content = data.get("generated_content", "")

        # Создаем промпт на основе контента
        prompt = f"На основе этого текста поста: '{generated_content[:200]}...' \n\nСоздай изображение в {style}."

    else:
        # Используем пользовательский промпт
        user_description = data.get("image_description", "")
        prompt = f"{user_description}. Стиль: {style}."

    await state.update_data(selected_style=style, final_prompt=prompt)

    # Запрашиваем размер изображения
    await callback.message.answer(
        f"✅ Выбран стиль: **{style}**\n\n"
        "📐 **Выберите размер изображения:**",
        reply_markup=IMAGE_SIZE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_image_size)


# === ОБРАБОТЧИКИ ВЫБОРА РАЗМЕРА ИЗОБРАЖЕНИЯ ===
@image_generation_router.callback_query(F.data == "image_size_1024x1024")
async def image_size_1024x1024_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора размера 1024x1024."""
    await callback.answer()
    await generate_final_image(callback, state, 1024, 1024)


@image_generation_router.callback_query(F.data == "image_size_1200x630")
async def image_size_1200x630_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора размера 1200x630."""
    await callback.answer()
    await generate_final_image(callback, state, 1200, 630)


@image_generation_router.callback_query(F.data == "image_size_630x1200")
async def image_size_630x1200_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора размера 630x1200."""
    await callback.answer()
    await generate_final_image(callback, state, 630, 1200)


async def generate_final_image(callback: CallbackQuery, state: FSMContext, width: int, height: int):
    """Генерация финального изображения."""
    data = await state.get_data()
    prompt = data.get("final_prompt", "")

    await callback.message.answer(
        f"🎨 **Генерирую изображение...**\n\n"
        f"📝 Промпт: {prompt[:100]}...\n"
        f"📐 Размер: {width}x{height}\n\n"
        "_Это может занять 30-60 секунд..._",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Получаем сервис генерации изображений
        image_service: ImageGenerationService = dispatcher["image_generation_service"]

        if not image_service:
            raise Exception("Сервис генерации изображений не настроен")

        # Генерируем изображение
        image_bytes = await image_service.generate_image(
            prompt=prompt,
            width=width,
            height=height,
        )

        # Создаем файл для отправки
        from aiogram.types.input_file import BufferedInputFile
        image_file = BufferedInputFile(image_bytes, "generated_image.png")

        await callback.message.answer_photo(
            photo=image_file,
            caption="✅ **Изображение готово!**\n\nЧто вы хотите сделать дальше?",
            reply_markup=IMAGE_GENERATION_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )

        await state.clear()

    except Exception as e:
        logger.exception("Ошибка при генерации изображения")
        await callback.message.answer(
            f"❌ **Ошибка генерации**\n\n"
            f"Не удалось сгенерировать изображение: {str(e)}\n\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=IMAGE_GENERATION_KEYBOARD,
        )
        await state.clear()


# === ОБРАБОТЧИКИ СООБЩЕНИЙ ДЛЯ ОПИСАНИЯ ИЗОБРАЖЕНИЯ ===
@image_generation_router.message(ContentGeneration.waiting_for_image_description, F.text)
async def process_image_description(message: Message, state: FSMContext):
    """Обработка описания изображения."""
    description = message.text.strip()

    if not description:
        await message.answer("⚠️ Пожалуйста, опишите изображение.")
        return

    await state.update_data(image_description=description)
    await state.set_state(ContentGeneration.waiting_for_image_style)

    await message.answer(
        f"✅ Описание сохранено: **{description[:100]}...**\n\n"
        "🎭 **Выберите стиль генерации:**",
        reply_markup=IMAGE_STYLE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )



# === ОБРАБОТЧИКИ ВЫБОРА ФОТО ДЛЯ КАРТОЧКИ ===
@image_generation_router.callback_query(F.data == "card_photo_ai")
async def card_photo_ai_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора ИИ для генерации фото карточки."""
    await callback.answer()
    await card_photo_handler_common(callback, state, "🤖 AI сгенерирует фото")


@image_generation_router.callback_query(F.data == "card_photo_upload")
async def card_photo_upload_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора загрузки своего фото для карточки."""
    await callback.answer()
    await card_photo_handler_common(callback, state, "📎 Загрузить своё фото")


@image_generation_router.callback_query(F.data == "card_photo_none")
async def card_photo_none_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора без фото для карточки."""
    await callback.answer()
    await card_photo_handler_common(callback, state, "🚫 Без фото")

POST_GENERATION_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Создать ещё", callback_data="create_again")],
        [InlineKeyboardButton(text="💡 Советы по продвижению", callback_data="get_tips")],
        [InlineKeyboardButton(text="✏️ Переработать текст", callback_data="refactor_content")]
    ]
)

@image_generation_router.callback_query(F.data == "back_to_confirmation")
async def back_to_confirmation_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к подтверждению генерации."""
    await callback.answer()
    await callback.message.answer(
        "✨ Что хотите сделать дальше?",
        reply_markup=POST_GENERATION_KEYBOARD,
    )
    await state.set_state(ContentGeneration.waiting_for_confirmation)


@image_generation_router.callback_query(F.data == "back_to_platform")
async def back_to_platform_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору платформы."""
    await callback.answer()
    await callback.message.answer(
        "📱 **На какой платформе будет публиковаться пост?**",
        reply_markup=PLATFORM_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_platform)





async def card_photo_handler_common(callback: CallbackQuery, state: FSMContext, card_source: str):
    """Общий обработчик для выбора источника фото для карточки."""
    await state.update_data(card_image_source=card_source)

    if card_source == "🤖 AI сгенерирует фото":
        # Переходим к запросу промпта для генерации фото карточки
        await callback.message.answer(
            "🎨 **Опишите желаемое фото для карточки**\n"
            "Опишите, какое фото должно быть на карточке. "
            "Можете упомянуть тему, композицию, стиль.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_card_photo_prompt)
    elif card_source == "📎 Загрузить своё фото":
        await callback.message.answer(
            "📎 **Загрузите фото для карточки**\n"
            "Пришлите фотографию, которая будет использована в карточке. "
            "Поддерживаемые форматы: JPEG, PNG.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_card_user_photo)
    else:  # "🚫 Без фото"
        await state.update_data(card_image_source="🚫 Без фото")
        await callback.message.answer(
            "✅ **Выбрано: Без фото для карточки**\n"
            "🎨 Переходим к генерации карточек...",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Переходим к генерации карточек без фото
        await generate_cards_handler(callback.message, state)


@image_generation_router.message(ContentGeneration.waiting_for_card_photo_prompt, F.text)
async def handle_card_photo_prompt(message: Message, state: FSMContext):
    """Обработчик для описания фото карточки."""
    card_prompt = message.text.strip()
    if not card_prompt:
        await message.answer(
            "Пожалуйста, опишите желаемое фото для карточки.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(card_image_prompt=card_prompt)

    # Переходим к генерации карточек
    await generate_cards_handler(message, state)


@image_generation_router.message(ContentGeneration.waiting_for_card_user_photo, F.photo)
async def handle_card_user_photo(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского фото для карточки."""
    if not message.photo:
        await message.answer(
            "Пожалуйста, загрузите изображение (фото).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Получаем наибольшее по размеру фото для лучшего качества
    photo = message.photo[-1]

    # Скачиваем изображение

    try:
        image_file = await bot.download(photo.file_id, destination=None)
        image_bytes = image_file.read()

        await state.update_data(card_user_image=image_bytes)

        await message.answer(
            "✅ Фото для карточки загружено!\n"
            "🎨 Создаем карточки с вашим фото...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации карточек
        await generate_cards_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке фото для карточки: {e}")
        await message.answer(
            "❌ Ошибка при загрузке фото. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


@image_generation_router.message(ContentGeneration.waiting_for_card_user_photo, F.document)
async def handle_card_user_document(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского документа с фото для карточки."""
    if not message.document:
        return

    # Проверяем, что это изображение
    mime_type = message.document.mime_type
    if not mime_type or not mime_type.startswith('image/'):
        await message.answer(
            "Пожалуйста, отправьте файл с изображением (JPEG, PNG).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    try:
        document_file = await bot.download(message.document.file_id, destination=None)
        image_bytes = document_file.read()

        await state.update_data(card_user_image=image_bytes)

        await message.answer(
            "✅ Фото для карточки загружено!\n"
            "🎨 Создаем карточки с вашим фото...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации карточек
        await generate_cards_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с фото для карточки: {e}")
        await message.answer(
            "❌ Ошибка при загрузке фото. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


# === ДОБАВЛЕННЫЕ ОБРАБОТЧИКИ КОНТЕНТ-ПЛАНА ===
# TODO: Эти обработчики нужно добавить в content_plan_generation.py как message handlers
# Сейчас они удалены из callbacks.py, поскольку @callbacks_router.callback_query не подходит для текстовых сообщений



# FIXME: не используются

# -- Формы создания контента --

CONTENT_FORM_MENU_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Структурированная форма", callback_data="structured_content")],
        [InlineKeyboardButton(text="💭 Свободная форма", callback_data="free_form_content")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_content_menu")]
    ]
)


@image_generation_router.callback_query(F.data == "create_content_form")
async def create_content_form_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора формы создания контента."""
    await callback.answer()

    await callback.message.answer(
        "📝 Создание контента\n\n"
        "Выберите форму создания:",
        reply_markup=CONTENT_FORM_MENU_KEYBOARD,
    )


@image_generation_router.callback_query(F.data == "back_to_content_menu")
async def back_to_content_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат непосредственно в главное меню (минуя промежуточный шаг)."""
    from bot.handlers.start import start_handler

    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


@image_generation_router.callback_query(F.data == "yes_fill_ngo")
async def yes_fill_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик согласия заполнить данные НКО."""
    await callback.answer()
    await fill_ngo_handler(callback, state)


@image_generation_router.callback_query(F.data == "no_fill_ngo")
async def no_fill_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отказа заполнить данные НКО."""
    await callback.answer()
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "")
    await callback.message.answer(
        "✨ Понятно! Создаем контент без упоминания НКО.\n\n"
    )
    if generation_mode == "structured":
        # Переход к структурированной форме без НКО
        await structured_generation_handler(callback.message, state)
    elif generation_mode == "free_form":
        # Переход к свободной форме без НКО
        await free_form_generation_handler(callback.message, state)


NGO_DATA_MISSING_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="yes_fill_ngo"),
         InlineKeyboardButton(text="❌ Нет", callback_data="no_fill_ngo")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_MAIN_MENU_CALLBACK_DATA)]
    ]
)

YES_NO_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="yes"),
         InlineKeyboardButton(text="❌ Нет", callback_data="no")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_MAIN_MENU_CALLBACK_DATA)]
    ]
)


@image_generation_router.callback_query(F.data == "structured_content")
async def structured_content_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик структурированной формы."""
    await callback.answer()
    await state.clear()
    await state.update_data(generation_mode="structured", has_ngo_info=False)

    # Проверяем наличие данных НКО
    ngo_service: NGOService = dispatcher["ngo_service"]
    user_id = callback.from_user.id

    if not ngo_service.ngo_exists(user_id):
        # Если данных НКО нет, предлагаем заполнить

        await callback.message.answer(
            "📋 Структурированная форма\n\n"
            "У вас нет сохраненной информации об НКО. Хотите заполнить ее сейчас?",
            reply_markup=NGO_DATA_MISSING_KEYBOARD,
        )
    else:
        # Если данные НКО есть, спрашиваем использовать ли их
        await callback.message.answer(
            "📋 Структурированная форма\n\n"
            "Для создания персонализированного контента с данными НКО - выберите 'Да'.\n"
            "Или продолжите без данных НКО - выберите 'Нет'.",
            reply_markup=YES_NO_KEYBOARD
        )
        await state.set_state(ContentGeneration.waiting_for_ngo_info_choice)


@image_generation_router.callback_query(F.data == "free_form_content")
async def free_form_content_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик свободной формы."""
    await callback.answer()
    await state.clear()
    await state.update_data(generation_mode="free_form", has_ngo_info=False)

    # Проверяем наличие данных НКО
    ngo_service: NGOService = dispatcher["ngo_service"]
    user_id = callback.from_user.id

    if not ngo_service.ngo_exists(user_id):
        # Если данных НКО нет, предлагаем заполнить

        await callback.message.answer(
            "💭 Свободная форма\n\n"
            "У вас нет сохраненной информации об НКО. Хотите заполнить ее сейчас?",
            reply_markup=NGO_DATA_MISSING_KEYBOARD,
        )
    else:
        # Если данные НКО есть, спрашиваем использовать ли их
        await callback.message.answer(
            "💭 Свободная форма\n\n"
            "Для создания персонализированного контента с данными НКО - выберите 'Да'.\n"
            "Или продолжите без данных НКО - выберите 'Нет'.",
            reply_markup=YES_NO_KEYBOARD,
        )
        await state.set_state(ContentGeneration.waiting_for_ngo_info_choice)




