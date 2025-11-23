import logging

from aiogram import Router, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.states import ContentGeneration, EditText
from bot.keyboards.inline import (
    get_narrative_style_keyboard,
    get_platform_keyboard,
    get_yes_no_keyboard,
    get_image_source_keyboard,
)
from app import bot

logger = logging.getLogger(__name__)

new_generation_router = Router(name="new_generation")


@new_generation_router.message(ContentGeneration.waiting_for_ngo_info_choice, F.text)
async def ngo_info_choice_handler(message: Message, state: FSMContext):
    """Обработчик выбора использования данных НКО."""
    answer = message.text.strip()

    if answer not in ["✅ Да", "❌ Нет"]:
        await message.answer(
            "Пожалуйста, используйте кнопки «Да» или «Нет».",
            reply_markup=get_yes_no_keyboard(),
        )
        return

    has_ngo = answer == "✅ Да"
    data = await state.get_data()
    generation_mode = data.get("generation_mode", "structured")
    edit_text = data.get("edit_text", False)

    if has_ngo:
        # Получаем данные НКО из БД
        from app import dp
        ngo_service = dp["ngo_service"]
        user_id = message.from_user.id
        ngo_data = ngo_service.get_ngo_data(user_id)

        if ngo_data:
            await state.update_data(
                has_ngo_info=True,
                ngo_name=ngo_data.get("ngo_name", ""),
                ngo_description=ngo_data.get("ngo_description", ""),
                ngo_activities=ngo_data.get("ngo_activities", ""),
                ngo_contact=ngo_data.get("ngo_contact", ""),
            )
        else:
            await message.answer(
                "⚠️ Данные НКО не найдены. Продолжаем без данных НКО.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.update_data(has_ngo_info=False)
    else:
        await state.update_data(has_ngo_info=False)

    # Переходим к соответствующему режиму
    if edit_text:
        # Режим редактирования текста
        await message.answer(
            "✏️ Отлично! Теперь введите текст, который нужно отредактировать.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(EditText.waiting_for_text)
    elif generation_mode == "structured":
        await message.answer(
            "📝 Отлично! Начинаем структурированную форму.\n\n"
            "**Что за событие?**\n"
            "Опишите коротко, о каком событии будет пост.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_event_type)
    else:  # free_form
        await message.answer(
            "💭 Понятно! Используем свободную форму.\n\n"
            "**Опишите ваш пост**\n"
            "Расскажите подробно, о чём будет пост, какую информацию нужно донести.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_user_description)


# ===============================
# СТРУКТУРИРОВАННАЯ ФОРМА
# ===============================

@new_generation_router.message(ContentGeneration.waiting_for_event_type, F.text)
async def event_type_handler(message: Message, state: FSMContext):
    """Обработчик для типа события."""
    event_type = message.text.strip()
    if not event_type:
        await message.answer(
            "Пожалуйста, опишите событие.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(event_type=event_type)

    await message.answer(
        "📅 **Когда состоится событие?**\n"
        "Укажите дату и время проведения.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_event_date)


@new_generation_router.message(ContentGeneration.waiting_for_event_date, F.text)
async def event_date_handler(message: Message, state: FSMContext):
    """Обработчик для даты события."""
    event_date = message.text.strip()
    if not event_date:
        await message.answer(
            "Пожалуйста, укажите дату и время.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(event_date=event_date)

    await message.answer(
        "📍 **Где состоится событие?**\n"
        "Укажите место проведения.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_event_place)


@new_generation_router.message(ContentGeneration.waiting_for_event_place, F.text)
async def event_place_handler(message: Message, state: FSMContext):
    """Обработчик для места события."""
    event_place = message.text.strip()
    if not event_place:
        await message.answer(
            "Пожалуйста, укажите место проведения.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(event_place=event_place)

    await message.answer(
        "👥 **Кто приглашен на событие?**\n"
        "Укажите целевую аудиторию (например: волонтеры, дети, родители, пенсионеры).",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_event_audience)


@new_generation_router.message(ContentGeneration.waiting_for_event_audience, F.text)
async def event_audience_handler(message: Message, state: FSMContext):
    """Обработчик для аудитории события."""
    event_audience = message.text.strip()
    if not event_audience:
        await message.answer(
            "Пожалуйста, укажите целевую аудиторию.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(event_audience=event_audience)

    await message.answer(
        "📝 **Дополнительные детали**\n"
        "Расскажите подробнее о событии: что будет интересного, зачем нужно участие, какая польза для участников.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_event_details)


@new_generation_router.message(ContentGeneration.waiting_for_event_details, F.text)
async def event_details_handler(message: Message, state: FSMContext):
    """Обработчик для дополнительных деталей события."""
    event_details = message.text.strip()

    await state.update_data(event_details=event_details)

    await message.answer(
        "🎨 **Выберите стиль повествования поста**",
        reply_markup=get_narrative_style_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_narrative_style)


@new_generation_router.message(ContentGeneration.waiting_for_narrative_style, F.text)
async def narrative_style_handler(message: Message, state: FSMContext):
    """Обработчик для стиля повествования."""
    style = message.text.strip()

    narrative_styles = [
        "💬 Разговорный стиль",
        "📋 Официально-деловой стиль",
        "🎨 Художественный стиль",
        "🌟 Позитивный/мотивирующий стиль",
    ]

    if style not in narrative_styles:
        await message.answer(
            "Пожалуйста, выберите стиль из списка.",
            reply_markup=get_narrative_style_keyboard(),
        )
        return

    await state.update_data(narrative_style=style)

    await message.answer(
        "📱 **На какой платформе будет публиковаться пост?**",
        reply_markup=get_platform_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_platform)


@new_generation_router.message(ContentGeneration.waiting_for_platform, F.text)
async def platform_handler(message: Message, state: FSMContext):
    """Обработчик для выбора платформы - переход к выбору изображения."""
    platform = message.text.strip()
    
    platform_options = [
        "📱 ВКонтакте (для молодежи)",
        "💬 Telegram (для взрослых/бизнеса)",
        "📸 Instagram (визуальный контент)",
    ]
    
    if platform not in platform_options:
        await message.answer(
            "Пожалуйста, выберите платформу из списка.",
            reply_markup=get_platform_keyboard(),
        )
        return

    await state.update_data(platform=platform)
    
    # Новый шаг: выбор источника изображения
    await message.answer(
        "🖼️ **Выберите источник тематической картинки для карточки:**",
        reply_markup=get_image_source_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_image_source)


# Добавляем обработчик для выбора источника изображения
@new_generation_router.message(ContentGeneration.waiting_for_image_source, F.text)
async def image_source_handler(message: Message, state: FSMContext):
    """Обработчик для выбора источника изображения."""
    image_source = message.text.strip()

    image_source_options = [
        "🤖 Сгенерировать ИИ",
        "📎 Загрузить своё",
        "🚫 Без фото",
    ]

    if image_source not in image_source_options:
        await message.answer(
            "Пожалуйста, выберите источник изображения.",
            reply_markup=get_image_source_keyboard(),
        )
        return

    await state.update_data(image_source=image_source)

    if image_source == "🤖 Сгенерировать ИИ":
        # Переходим к генерации ИИ
        await message.answer(
            "🎨 **Опишите желаемую картинку для карточки**\n"
            "Опишите, как должна выглядеть иллюстрация к вашему посту. "
            "Можете упомянуть стиль, цвета, настроение.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_image_prompt)
    elif image_source == "📎 Загрузить своё":
        await message.answer(
            "📎 **Загрузите изображение**\n"
            "Пришлите фотографию или изображение, которое будет использовано в карточке. "
            "Поддерживаемые форматы: JPEG, PNG.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_user_image)
    else:  # "🚫 Без фото"
        await message.answer(
            "✅ **Выбрано: Без фото**\n"
            "🎨 Создаем контент без изображения...",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Переходим к генерации контента без фото
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)


@new_generation_router.message(ContentGeneration.waiting_for_image_prompt, F.text)
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
    from bot.handlers.generation import complete_generation_handler
    await complete_generation_handler(message, state)


@new_generation_router.message(ContentGeneration.waiting_for_user_image, F.photo)
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
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке изображения: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


@new_generation_router.message(ContentGeneration.waiting_for_user_image, F.document)
async def user_document_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского документа с изображением."""
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

    from app import dp
    bot = dp["bot"]

    try:
        document_file = await bot.download(message.document.file_id, destination=None)
        image_bytes = document_file.read()

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с изображением: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


# ===============================
# СВОБОДНАЯ ФОРМА
# ===============================

@new_generation_router.message(ContentGeneration.waiting_for_user_description, F.text)
async def user_description_handler(message: Message, state: FSMContext):
    """Обработчик для описания пользователя в свободной форме."""
    user_description = message.text.strip()
    if not user_description:
        await message.answer(
            "Пожалуйста, опишите ваш пост.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(user_text=user_description)

    await message.answer(
        "🎨 **Выберите стиль повествования поста**",
        reply_markup=get_narrative_style_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_free_style)


@new_generation_router.message(ContentGeneration.waiting_for_free_style, F.text)
async def free_style_handler(message: Message, state: FSMContext):
    """Обработчик для стиля повествования в свободной форме."""
    style = message.text.strip()

    narrative_styles = [
        "💬 Разговорный стиль",
        "📋 Официально-деловой стиль",
        "🎨 Художественный стиль",
        "🌟 Позитивный/мотивирующий стиль",
    ]

    if style not in narrative_styles:
        await message.answer(
            "Пожалуйста, выберите стиль из списка.",
            reply_markup=get_narrative_style_keyboard(),
        )
        return

    await state.update_data(narrative_style=style)

    await message.answer(
        "📱 **На какой платформе будет публиковаться пост?**",
        reply_markup=get_platform_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_free_platform)


@new_generation_router.message(ContentGeneration.waiting_for_free_platform, F.text)
async def free_platform_handler(message: Message, state: FSMContext):
    """Обработчик для выбора платформы в свободной форме - переход к выбору изображения."""
    platform = message.text.strip()

    platform_options = [
        "📱 ВКонтакте (для молодежи)",
        "💬 Telegram (для взрослых/бизнеса)",
        "📸 Instagram (визуальный контент)",
    ]

    if platform not in platform_options:
        await message.answer(
            "Пожалуйста, выберите платформу из списка.",
            reply_markup=get_platform_keyboard(),
        )
        return

    await state.update_data(platform=platform)

    # Новый шаг: выбор источника изображения
    await message.answer(
        "🖼️ **Выберите источник тематической картинки для карточки:**",
        reply_markup=get_image_source_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_free_image_source)


@new_generation_router.message(ContentGeneration.waiting_for_free_image_source, F.text)
async def free_image_source_handler(message: Message, state: FSMContext):
    """Обработчик для выбора источника изображения в свободной форме."""
    image_source = message.text.strip()

    image_source_options = [
        "🤖 Сгенерировать ИИ",
        "📎 Загрузить своё",
        "🚫 Без фото",
    ]

    if image_source not in image_source_options:
        await message.answer(
            "Пожалуйста, выберите источник изображения.",
            reply_markup=get_image_source_keyboard(),
        )
        return

    await state.update_data(image_source=image_source)

    if image_source == "🤖 Сгенерировать ИИ":
        # Переходим к генерации ИИ
        await message.answer(
            "🎨 **Опишите желаемую картинку для карточки**\n"
            "Опишите, как должна выглядеть иллюстрация к вашему посту. "
            "Можете упомянуть стиль, цвета, настроение.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_free_image_prompt)
    elif image_source == "📎 Загрузить своё":
        await message.answer(
            "📎 **Загрузите изображение**\n"
            "Пришлите фотографию или изображение, которое будет использовано в карточке. "
            "Поддерживаемые форматы: JPEG, PNG.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_free_user_image)
    else:  # "🚫 Без фото"
        await message.answer(
            "✅ **Выбрано: Без фото**\n"
            "🎨 Создаем контент без изображения...",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Переходим к генерации контента без фото
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)


@new_generation_router.message(ContentGeneration.waiting_for_free_image_prompt, F.text)
async def free_image_prompt_handler(message: Message, state: FSMContext):
    """Обработчик для описания изображения ИИ в свободной форме."""
    image_prompt = message.text.strip()
    if not image_prompt:
        await message.answer(
            "Пожалуйста, опишите желаемое изображение.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(image_prompt=image_prompt)

    # Переходим к генерации контента
    from bot.handlers.generation import complete_generation_handler
    await complete_generation_handler(message, state)


@new_generation_router.message(ContentGeneration.waiting_for_free_user_image, F.photo)
async def free_user_image_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского изображения в свободной форме."""
    if not message.photo:
        await message.answer(
            "Пожалуйста, загрузите изображение (фото).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Получаем наибольшее по размеру фото для лучшего качества
    photo = message.photo[-1]

    # Скачиваем изображение
    from app import dp
    bot = dp["bot"]

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
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке изображения: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )


@new_generation_router.message(ContentGeneration.waiting_for_free_user_image, F.document)
async def free_user_document_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского документа с изображением в свободной форме."""
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

    from app import dp
    bot = dp["bot"]

    try:
        document_file = await bot.download(message.document.file_id, destination=None)
        image_bytes = document_file.read()

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        from bot.handlers.generation import complete_generation_handler
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с изображением: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )
