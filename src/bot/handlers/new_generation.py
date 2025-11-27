import logging

from aiogram import Router, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, dispatcher
from bot.handlers.wizard_handler import NARRATIVE_STYLE_KEYBOARD
from bot.states import ContentGeneration, EditText
from services.ngo_service import NGOService
from services.text_generation import TextGenerationService

logger = logging.getLogger(__name__)

new_generation_router = Router(name="new_generation")



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
        reply_markup=NARRATIVE_STYLE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_narrative_style)







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
        reply_markup=NARRATIVE_STYLE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentGeneration.waiting_for_free_style)





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
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с изображением: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )



@new_generation_router.message(ContentGeneration.waiting_for_image_prompt, F.text)
async def callback_image_prompt_handler(message: Message, state: FSMContext):
    """Обработчик для описания изображения ИИ в callbacks flow."""
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


@new_generation_router.message(ContentGeneration.waiting_for_user_image, F.photo)
async def callback_user_image_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского изображения в callbacks flow."""
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


@new_generation_router.message(ContentGeneration.waiting_for_user_image, F.document)
async def callback_user_document_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского документа с изображением в callbacks flow."""
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

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с изображением: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )



@new_generation_router.message(ContentGeneration.waiting_for_free_image_prompt, F.text)
async def callback_free_image_prompt_handler(message: Message, state: FSMContext):
    """Обработчик для описания изображения ИИ в free form callbacks flow."""
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


@new_generation_router.message(ContentGeneration.waiting_for_free_user_image, F.photo)
async def callback_free_user_image_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского изображения в free form callbacks flow."""
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


@new_generation_router.message(ContentGeneration.waiting_for_free_user_image, F.document)
async def callback_free_user_document_handler(message: Message, state: FSMContext):
    """Обработчик для загрузки пользовательского документа с изображением в free form callbacks flow."""
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

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ Изображение загружено!\n"
            "🎨 Создаем контент с вашим изображением...",
            reply_markup=ReplyKeyboardRemove(),
        )

        # Переходим к генерации контента
        await complete_generation_handler(message, state)

    except Exception as e:
        logger.exception(f"Ошибка при загрузке документа с изображением: {e}")
        await message.answer(
            "❌ Ошибка при загрузке изображения. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove(),
        )



async def free_image_source_handler_common(callback: CallbackQuery, state: FSMContext, image_source: str):
    """Общий обработчик для выбора источника изображения в free form."""
    await state.update_data(image_source=image_source)

    if image_source == "🤖 Сгенерировать ИИ":
        # Переходим к генерации ИИ для free form
        await callback.message.answer(
            "🎨 **Опишите желаемую картинку для карточки**\n"
            "Опишите, как должна выглядеть иллюстрация к вашему посту. "
            "Можете упомянуть стиль, цвета, настроение.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_free_image_prompt)
    elif image_source == "📎 Загрузить своё":
        await callback.message.answer(
            "📎 **Загрузите изображение**\n"
            "Пришлите фотографию или изображение, которое будет использовано в карточке. "
            "Поддерживаемые форматы: JPEG, PNG.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentGeneration.waiting_for_free_user_image)
    else:  # "🚫 Без фото"
        await callback.message.answer(
            "✅ **Выбрано: Без фото**\n"
            "🎨 Создаем контент без изображения...",
            reply_markup=ReplyKeyboardRemove(),
        )
        # Переходим к генерации контента без фото
        await complete_generation_handler(callback.message, state)

# === ОБРАБОТЧИКИ ВЫБОРА ИСТОЧНИКА ИЗОБРАЖЕНИЯ ===
