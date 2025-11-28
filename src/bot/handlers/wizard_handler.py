import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardRemove, FSInputFile
from aiogram.enums.parse_mode import ParseMode
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup

from bot import dispatcher
from bot.states import ContentWizard
from services.ngo_service import NGOService

from services.card_generation import CardGenerationService
from services.text_generation import TextGenerationService

from bot.states import ContentGeneration

from models import Ngo

from bot import bot

from dtos import PromptContext

BACK_TO_MAIN_MENU_CALLBACK_DATA = "back_to_main"


YES_NO_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="yes"),
         InlineKeyboardButton(text="❌ Нет", callback_data="no")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_MAIN_MENU_CALLBACK_DATA)]
    ]
)


BACK_TO_START_MENU_CALLBACK_DATA = "back_to_start_menu"

logger = logging.getLogger(__name__)

create_content_wizard = Router(name="wizard")


WIZARD_CREATE_CONTENT = "create_content_wizard"



# ===== ЭТАП 1: ЗАПУСК WIZARD =====

"""Клавиатура выбора режима генерации контента для Wizard."""
CONTENT_WIZARD_SELECT_MODE_KEYBOARD: InlineKeyboardMarkup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Структурированная форма", callback_data="create_content_wizard_structured")],
            [InlineKeyboardButton(text="💭 Свободная форма", callback_data="wizard_free")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_START_MENU_CALLBACK_DATA)]
        ]
    )



@create_content_wizard.callback_query(F.data == WIZARD_CREATE_CONTENT)
async def start_wizard_handler(callback: CallbackQuery, state: FSMContext):
    """Запуск Мастера для создания контента."""
    await callback.answer()
    await state.clear()
    await state.set_state(ContentWizard.waiting_for_wizard_mode)

    await callback.message.answer(
        "🎨 **Мастер создания контента**\n\n"
        "Добро пожаловать в пошаговый режим создания контента! "
        "Мы проведем вас через все этапы:\n\n"
        "1️⃣ Выбор формы генерации\n"
        "2️⃣ Генерация текста с возможностью редактирования\n"
        "3️⃣ Настройка изображений\n"
        "4️⃣ Финальная генерация контента\n\n"
        "**Выберите форму создания:**",
        reply_markup=CONTENT_WIZARD_SELECT_MODE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )


# ===== ЭТАП 1: ВЫБОР РЕЖИМА =====

# FIXME: Этот обработчик реально используется
@create_content_wizard.callback_query(F.data == "create_content_wizard_structured")
async def wizard_structured_mode_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора структурированной формы."""
    from bot.handlers.start import BACK_TO_START_KEYBOARD
    await callback.answer()
    await state.update_data(wizard_mode="structured")

    # Проверяем наличие данных НКО
    ngo_service: NGOService = dispatcher["ngo_service"]
    user_id: int = callback.from_user.id

    has_ngo_data: bool = ngo_service.ngo_exists(user_id)

    if has_ngo_data:
        ngo_data: Ngo = ngo_service.get_ngo_data_by_user_id(user_id)
        ngo_name: str = ngo_data.name

        await callback.message.answer(
            f"📋 **Структурированная форма**\n\n"
            f"У вас есть данные НКО: **{ngo_name}**\n\n"
            f"Использовать данные НКО в контенте?",
            reply_markup=YES_NO_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await callback.message.answer(
            "📋 **Структурированная форма**\n\n"
            "У вас нет сохраненных данных об НКО.\n\n"
            "Хотите заполнить их перед созданием контента?\n\n"
            "_Это поможет сделать контент персонализированным._",
            reply_markup=YES_NO_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )

    await state.set_state(ContentWizard.waiting_for_wizard_ngo)


@create_content_wizard.callback_query(F.data == "wizard_free")
async def wizard_free_mode_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора свободной формы."""
    await callback.answer()
    await state.update_data(wizard_mode="free")

    # Проверяем наличие данных НКО
    ngo_service: NGOService = dispatcher["ngo_service"]
    user_id = callback.from_user.id

    has_ngo_data = ngo_service.ngo_exists(user_id)

    if has_ngo_data:
        ngo_data = ngo_service.get_ngo_data_by_user_id(user_id)
        ngo_name = ngo_data.name

        await callback.message.answer(
            f"💭 **Свободная форма**\n\n"
            f"У вас есть данные НКО: **{ngo_name}**\n\n"
            f"Использовать данные НКО в контенте?",
            reply_markup=YES_NO_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await callback.message.answer(
            "💭 **Свободная форма**\n\n"
            "Вы сможете самостоятельно описать содержание поста.\n\n"
            "Хотите сначала заполнить данные о вашей НКО?\n\n"
            "_Это пригодится для будущих генераций контента._",
            reply_markup=YES_NO_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )

    await state.set_state(ContentWizard.waiting_for_wizard_ngo)



# ===== ЭТАП 1: ОБРАБОТКА ВЫБОРА НКО =====

@create_content_wizard.callback_query(F.data == "yes", ContentWizard.waiting_for_wizard_ngo)
async def wizard_yes_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Пользователь согласился использовать данные НКО."""
    await callback.answer()

    ngo_service = dispatcher["ngo_service"]
    user_id = callback.from_user.id

    ngo_data: Ngo = ngo_service.get_ngo_data_by_user_id(user_id)
    await state.update_data({"ngo_data": ngo_data})
    await wizard_proceed_to_text_setup(callback, state)


@create_content_wizard.callback_query(F.data == "no", ContentWizard.waiting_for_wizard_ngo)
async def wizard_no_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Пользователь отказался использовать данные НКО."""
    await callback.answer()
    await state.update_data(has_ngo_info=False)
    await wizard_proceed_to_text_setup(callback, state)


async def wizard_proceed_to_text_setup(callback: CallbackQuery, state: FSMContext):
    """Переход к этапу настройки текста."""
    data = await state.get_data()
    wizard_mode = data.get("wizard_mode", "structured")

    text = "📝 **Этап 2: Настройка текста**\n\n"


    if wizard_mode == "structured":
        text += (
            "Давайте настроим параметры структурированного поста.\n\n"
            "**Что за событие?**\n"
            "Опишите коротко, о каком событии будет пост."
        )

        await state.set_state(ContentWizard.waiting_for_wizard_text_setup)
    else:  # free form
        text += (
            "Опишите ваш пост свободно.\n\n"
            "**Расскажите подробно**\n"
            "Какая информация должна быть в посте, какую цель он преследует."
        )
        await state.set_state(ContentWizard.waiting_for_wizard_text_setup)

    from bot.handlers import TEXT_SETUP_PHOTO

    await callback.message.answer_photo(
        photo=TEXT_SETUP_PHOTO,
        caption=text,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

# ===== ЭТАП 2: НАСТРОЙКА ТЕКСТА =====

@create_content_wizard.message(ContentWizard.waiting_for_wizard_text_setup, F.text)
async def wizard_text_setup_handler(message: Message, state: FSMContext):
    """Обработка ввода параметров текста."""
    data = await state.get_data()
    wizard_mode = data.get("wizard_mode", "structured")

    from bot.handlers import CALENDAR_PHOTO

    if wizard_mode == "structured":
        # Структурированная форма: сохраняем тип события
        event_type = message.text.strip()
        await state.update_data(event_type=event_type)


        await message.answer_photo(
            photo=CALENDAR_PHOTO,
            caption="📅 **Когда состоится событие?**\n"
            "Укажите дату и время проведения.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentWizard.waiting_for_wizard_event_date)
    else:
        # Свободная форма: сохраняем описание и переходим к генерации
        await state.update_data(user_description=message.text.strip())
        await wizard_start_text_generation(message, state)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_date, F.text)
async def wizard_event_date_handler(message: Message, state: FSMContext):
    """Обработка даты события."""
    event_date = message.text.strip()
    await state.update_data(event_date=event_date)

    from bot.handlers import LOCATION_PHOTO

    await message.answer_photo(
        photo=LOCATION_PHOTO,
        caption="📍 **Где состоится событие?**\n"
        "Укажите место проведения.",
        parse_mode=ParseMode.MARKDOWN,
    )

    await state.set_state(ContentWizard.waiting_for_wizard_event_place)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_place, F.text)
async def wizard_event_place_handler(message: Message, state: FSMContext):
    """Обработка места события."""
    from bot.handlers import INSPECT_PHOTO

    event_place = message.text.strip()
    await state.update_data(event_place=event_place)

    await message.answer_photo(
        photo=INSPECT_PHOTO,
        caption="👥 **Кто приглашен на событие?**\n"
        "Укажите целевую аудиторию (волонтеры, дети, родители, пенсионеры).",
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_audience)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_audience, F.text)
async def wizard_event_audience_handler(message: Message, state: FSMContext):
    """Обработка аудитории события."""
    event_audience = message.text.strip()
    await state.update_data(event_audience=event_audience)
    from bot.handlers import TEXT_SETUP_PHOTO

    await message.answer_photo(
        photo=TEXT_SETUP_PHOTO,
        caption="📝 **Дополнительные детали**\n"
        "Расскажите подробнее о событии: что будет интересного, зачем участвовать.",
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_details)

NARRATIVE_STYLE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💬 Разговорный стиль", callback_data="narrative_conversational")],
        [InlineKeyboardButton(text="📋 Официально-деловой стиль", callback_data="narrative_official")],
        [InlineKeyboardButton(text="🎨 Художественный стиль", callback_data="narrative_artistic")],
        [InlineKeyboardButton(text="🌟 Позитивный/мотивирующий стиль", callback_data="narrative_motivational")],
        # TODO: Добавь указание своего стиля
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
    ]
)

@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_details, F.text)
async def wizard_event_details_handler(message: Message, state: FSMContext):
    """Обработка деталей события."""
    event_details = message.text.strip()
    await state.update_data(event_details=event_details)

    from bot.handlers import NARRATIVE_STYLE_PHOTO

    await message.answer_photo(
        photo=NARRATIVE_STYLE_PHOTO,
        caption="🎨 **Выберите стиль повествования:**",
        reply_markup=NARRATIVE_STYLE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_style)


@create_content_wizard.callback_query(F.data == "narrative_conversational", ContentWizard.waiting_for_wizard_event_style)
async def wizard_narrative_conversational_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(narrative_style="💬 Разговорный стиль")
    await wizard_proceed_to_platform(callback, state)


@create_content_wizard.callback_query(F.data == "narrative_official", ContentWizard.waiting_for_wizard_event_style)
async def wizard_narrative_official_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(narrative_style="📋 Официально-деловой стиль")
    await wizard_proceed_to_platform(callback, state)


@create_content_wizard.callback_query(F.data == "narrative_artistic", ContentWizard.waiting_for_wizard_event_style)
async def wizard_narrative_artistic_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(narrative_style="🎨 Художественный стиль")
    await wizard_proceed_to_platform(callback, state)

@create_content_wizard.callback_query(F.data == "narrative_motivational", ContentWizard.waiting_for_wizard_narrative_style_edit)
@create_content_wizard.callback_query(F.data == "narrative_motivational", ContentWizard.waiting_for_wizard_event_style)
async def wizard_narrative_motivational_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(narrative_style="🌟 Позитивный/мотивирующий стиль")
    await wizard_proceed_to_platform(callback, state)




async def wizard_proceed_to_platform(callback: CallbackQuery, state: FSMContext):
    """Переход к выбору платформы."""
    from bot.handlers import PLATFORM_PHOTO

    await callback.message.answer_photo(
        photo=PLATFORM_PHOTO,
        caption="📱 **На какой платформе будет опубликован пост?**",
        reply_markup=PLATFORM_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_platform)


@create_content_wizard.callback_query(F.data == "platform_vk", ContentWizard.waiting_for_wizard_platform_edit)
@create_content_wizard.callback_query(F.data == "platform_vk", ContentWizard.waiting_for_wizard_event_platform)
async def wizard_platform_vk_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(platform="📱 ВКонтакте (для молодежи)")
    await wizard_start_text_generation(callback.message, state)


@create_content_wizard.callback_query(F.data == "platform_telegram", ContentWizard.waiting_for_wizard_platform_edit)
@create_content_wizard.callback_query(F.data == "platform_telegram", ContentWizard.waiting_for_wizard_event_platform)
async def wizard_platform_telegram_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(platform="💬 Telegram (для взрослых/бизнеса)")
    await wizard_start_text_generation(callback.message, state)


@create_content_wizard.callback_query(F.data == "platform_website", ContentWizard.waiting_for_wizard_platform_edit)
@create_content_wizard.callback_query(F.data == "platform_website", ContentWizard.waiting_for_wizard_event_platform)
async def wizard_platform_website_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(platform="🌐 Сайт (для информационных материалов)")
    await wizard_start_text_generation(callback.message, state)


WIZARD_CONTENT_GENERATION_MANAGEMENT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="wizard_text_regenerate")],
        [InlineKeyboardButton(text="✏️ Исправить текст", callback_data="wizard_text_edit")],
        [InlineKeyboardButton(text="⚙️ Изменить параметры", callback_data="wizard_text_change_fields")],
        [InlineKeyboardButton(text="🎨 Генерация карточки", callback_data="wizard_to_image")],
        [InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="wizard_back_to_setup")]
    ]
)


async def wizard_start_text_generation(message_or_callback, state: FSMContext):
    """Запуск генерации текста."""
    from bot.handlers import TEXT_GENERATION_PHOTO

    await message_or_callback.answer_photo(
        photo=TEXT_GENERATION_PHOTO,
        caption="🧠 **Генерируем текст поста...**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Генерация текста
        text_generation_service = dispatcher["text_content_generation_service"]
        data = await state.get_data()
        user_text = ""
        if data["wizard_mode"] == "structured":
            context = PromptContext(
                event_type=data.get("event_type", ""),
                event_date=data.get("event_date", ""),
                event_place=data.get("event_place", ""),
                event_audience=data.get("event_audience", ""),
                narrative_style=data.get("narrative_style", ""),
                platform=data.get("platform", ""),
                has_ngo_info=data.get("has_ngo_info", ""),
                ngo_name=data.get("ngo_name", ""),
                ngo_description=data.get("ngo_description", ""),
                ngo_activities=data.get("ngo_activities", ""),
                ngo_contact=data.get("ngo_contact", ""),
            )
        else:
            user_text = data["user_description"]
            context = PromptContext(
                has_ngo_info=data.get("has_ngo_info", ""),
                ngo_name=data.get("ngo_name", ""),
                ngo_description=data.get("ngo_description", ""),
                ngo_activities=data.get("ngo_activities", ""),
                ngo_contact=data.get("ngo_contact", ""),
            )

        generated_text = await text_generation_service.generate_text(context, user_text)

        await state.update_data(generated_text=generated_text)

        await message_or_callback.answer(
            "✅ **Текст поста готов!**\n\n",
            parse_mode=ParseMode.MARKDOWN,
        )
        await message_or_callback.answer(
            f"{generated_text}\n\n",
            parse_mode=ParseMode.MARKDOWN,
        )
        await message_or_callback.answer(
            "**Что делать с текстом?**",
            reply_markup=WIZARD_CONTENT_GENERATION_MANAGEMENT_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentWizard.waiting_for_wizard_text_result)

    except Exception as e:
        logger.exception(f"Ошибка генерации текста: {e}")
        await message_or_callback.answer(
            "❌ Произошла ошибка при генерации текста. Попробуйте снова.",
            reply_markup=CONTENT_WIZARD_SELECT_MODE_KEYBOARD,
        )


# ===== ЭТАП 2: УПРАВЛЕНИЕ ТЕКСТОМ =====
WIZARD_TEXT_REGENERATE = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Случайные изменения", callback_data="wizard_regenerate_random")],
        [InlineKeyboardButton(text="✏️ Указать причину", callback_data="wizard_regenerate_custom")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="wizard_back_to_text_result")]
    ]
)


@create_content_wizard.callback_query(F.data == "wizard_text_regenerate")
async def wizard_text_regenerate_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик перегенерации текста."""
    await callback.answer()

    await callback.message.answer(
        "🔄 **Перегенерация текста**\n\n"
        "Выберите вариант генерации:",
        reply_markup=WIZARD_TEXT_REGENERATE,
    )


@create_content_wizard.callback_query(F.data == "wizard_text_edit")
async def wizard_text_edit_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик редактирования текста."""
    await callback.answer()

    await callback.message.answer(
        "✏️ **Редактирование текста**\n\n"
        "Опишите, как именно нужно изменить текст:\n\n"
        "_Например: «Сделаи короче», «Измени стиль», «Добавь призыв к действию»_",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_text_edit)


WIZARD_CONTENT_GENERATION_FIELD_SELECT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📝 Тип события", callback_data="wizard_edit_event_type")],
        [InlineKeyboardButton(text="📅 Дата события", callback_data="wizard_edit_event_date")],
        [InlineKeyboardButton(text="📍 Место события", callback_data="wizard_edit_event_place")],
        [InlineKeyboardButton(text="👥 Аудитория", callback_data="wizard_edit_event_audience")],
        [InlineKeyboardButton(text="📝 Детали события", callback_data="wizard_edit_event_details")],
        [InlineKeyboardButton(text="🎨 Стиль повествования", callback_data="wizard_edit_narrative_style")],
        [InlineKeyboardButton(text="📱 Платформа", callback_data="wizard_edit_platform")],
        [InlineKeyboardButton(text="✅ Сохранить и вернуться", callback_data="wizard_back_to_text_result")],
        [InlineKeyboardButton(text="⬅️ Назад к тексту", callback_data="wizard_back_to_text_result")]
    ]
)


@create_content_wizard.callback_query(F.data == "wizard_text_change_fields")
async def wizard_text_change_fields_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик изменения параметров структурированной формы."""
    await callback.answer()

    data = await state.get_data()
    wizard_mode = data.get("wizard_mode", "structured")

    if wizard_mode == "structured":
        await callback.message.answer(
            "⚙️ **Изменение параметров**\n\n"
            "Выберите, какое поле хотите изменить:",
            reply_markup=WIZARD_CONTENT_GENERATION_FIELD_SELECT_KEYBOARD,
        )
        await state.set_state(ContentWizard.waiting_for_wizard_field_select)
    else:
        await callback.message.answer(
            "ℹ️ **Изменение описания**\n\n"
            "В свободной форме вы можете изменить описание поста.\n\n"
            "Новое описание:",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(ContentWizard.waiting_for_wizard_text_field_select)


WIZARD_IMAGE_SOURCE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Сгенерировать ИИ", callback_data="wizard_image_ai")],
        [InlineKeyboardButton(text="📎 Загрузить своё", callback_data="wizard_image_upload")],
        [InlineKeyboardButton(text="🚫 Без фото", callback_data="wizard_image_none")],
        [InlineKeyboardButton(text="⬅️ Назад к тексту", callback_data="wizard_back_to_text")]
    ]
)


@create_content_wizard.callback_query(F.data == "wizard_to_image")
async def wizard_to_image_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик перехода к этапу работы с изображением."""
    await callback.answer()

    await callback.message.answer(
        "🖼️ **Этап 3: Работа с изображением**\n\n"
        "Выберите источник изображения для поста:",
        reply_markup=WIZARD_IMAGE_SOURCE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_image_source)


# ===== ОБРАБОТЧИКИ ПЕРЕГЕНЕРАЦИИ ТЕКСТА =====

@create_content_wizard.callback_query(F.data == "wizard_regenerate_random")
async def wizard_regenerate_random_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик случайной перегенерации текста."""
    await callback.answer()

    await callback.message.answer(
        "🔄 **Перегенерируем текст...**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    # Перегенерация с теми же параметрами
    await wizard_start_text_generation(callback.message, state)


@create_content_wizard.callback_query(F.data == "wizard_regenerate_custom")
async def wizard_regenerate_custom_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик перегенерации с указанием причины."""
    await callback.answer()

    await callback.message.answer(
        "🔄 **Перегенерация текста**\n\n"
        "Опишите, что именно нужно изменить в тексте:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_text_regenerate)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_text_regenerate, F.text)
async def wizard_text_regenerate_custom_handler(message: Message, state: FSMContext):
    """Обработка причины перегенерации текста."""
    regenerate_reason = message.text.strip()
    await state.update_data(regenerate_reason=regenerate_reason)

    await message.answer(
        "🔄 **Перегенерируем текст...**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    # Здесь должна быть логика использования причины перегенерации
    # Пока просто перегенерируем
    await wizard_start_text_generation(message, state)


# ===== ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ТЕКСТА =====

@create_content_wizard.message(ContentWizard.waiting_for_wizard_text_edit, F.text)
async def wizard_text_edit_handler(message: Message, state: FSMContext):
    """Обработка редактирования текста."""
    edit_instruction = message.text.strip()
    await state.update_data(edit_instruction=edit_instruction)

    await message.answer(
        "✏️ **Редактируем текст...**",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        # Получаем текущий сгенерированный текст
        data = await state.get_data()
        current_text = data.get["generated_text"]

        # Используем text_editing сервис для редактирования

        text_generation_service: TextGenerationService = TextGenerationService()
        edited_text = await text_generation_service.edit_text(
            text=current_text,
            instructions=edit_instruction
        )

        await state.update_data(generated_text=edited_text)

        await message.answer(
            "✅ **Текст отредактирован!**\n\n"
            f"{edited_text}\n\n"
            "**Что делать с текстом?**",
            reply_markup=WIZARD_CONTENT_GENERATION_MANAGEMENT_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentWizard.waiting_for_wizard_text_result)

    except Exception as e:
        logger.exception(f"Ошибка редактирования текста: {e}")
        await message.answer(
            "❌ Ошибка редактирования текста. Попробуйте снова.",
            reply_markup=WIZARD_CONTENT_GENERATION_MANAGEMENT_KEYBOARD,
        )


# ===== ОБРАБОТЧИКИ ИЗМЕНЕНИЯ ПОЛЕЙ =====

@create_content_wizard.callback_query(F.data == "wizard_edit_event_type")
async def wizard_edit_event_type_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📝 **Изменение типа события**\n\n"
        "Текущее значение -  сохранено. Новое значение:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_type_edit)


@create_content_wizard.callback_query(F.data == "wizard_edit_event_date")
async def wizard_edit_event_date_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📅 **Изменение даты события**\n\n"
        "Текущее значение - сохранено. Новое значение:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_date_edit)


@create_content_wizard.callback_query(F.data == "wizard_edit_event_place")
async def wizard_edit_event_place_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📍 **Изменение места события**\n\n"
        "Текущее значение - сохранено. Новое значение:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_place_edit)


@create_content_wizard.callback_query(F.data == "wizard_edit_event_audience")
async def wizard_edit_event_audience_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "👥 **Изменение аудитории**\n\n"
        "Текущее значение - сохранено. Новое значение:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_audience_edit)


@create_content_wizard.callback_query(F.data == "wizard_edit_event_details")
async def wizard_edit_event_details_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📝 **Изменение деталей события**\n\n"
        "Текущее значение - сохранено. Новое значение:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_event_details_edit)


@create_content_wizard.callback_query(F.data == "wizard_edit_narrative_style")
async def wizard_edit_narrative_style_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "🎨 **Изменение стиля повествования**",
        reply_markup=NARRATIVE_STYLE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_narrative_style_edit)

PLATFORM_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📱 ВКонтакте (для молодежи)", callback_data="platform_vk")],
        [InlineKeyboardButton(text="💬 Telegram (для взрослых/бизнеса)", callback_data="platform_telegram")],
        [InlineKeyboardButton(text="🌐 Сайт (для информационных материалов)", callback_data="platform_website")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_previous")]
    ]
)


@create_content_wizard.callback_query(F.data == "wizard_edit_platform")
async def wizard_edit_platform_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📱 **Изменение платформы**",
        reply_markup=PLATFORM_KEYBOARD,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_platform_edit)


@create_content_wizard.callback_query(F.data == "wizard_back_to_text_result")
async def wizard_back_to_text_result_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к результату генерации текста."""
    await callback.answer()

    data = await state.get_data()
    generated_text = data.get("generated_text", "")
    await callback.message.answer(
        f"✅ **Текст поста:**\n\n{generated_text}\n\n**Что делать с текстом?**",
        reply_markup=WIZARD_CONTENT_GENERATION_MANAGEMENT_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_text_result)


# ===== ОБРАБОТЧИКИ ИЗМЕНЕНИЯ ПОЛЕЙ (ВВОД ТЕКСТА) =====

@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_type_edit, F.text)
async def wizard_update_event_type_handler(message: Message, state: FSMContext):
    event_type = message.text.strip()
    await state.update_data(event_type=event_type)
    await wizard_regenerate_after_field_change(message, state)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_date_edit, F.text)
async def wizard_update_event_date_handler(message: Message, state: FSMContext):
    event_date = message.text.strip()
    await state.update_data(event_date=event_date)
    await wizard_regenerate_after_field_change(message, state)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_place_edit, F.text)
async def wizard_update_event_place_handler(message: Message, state: FSMContext):
    event_place = message.text.strip()
    await state.update_data(event_place=event_place)
    await wizard_regenerate_after_field_change(message, state)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_audience_edit, F.text)
async def wizard_update_event_audience_handler(message: Message, state: FSMContext):
    event_audience = message.text.strip()
    await state.update_data(event_audience=event_audience)
    await wizard_regenerate_after_field_change(message, state)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_event_details_edit, F.text)
async def wizard_update_event_details_handler(message: Message, state: FSMContext):
    event_details = message.text.strip()
    await state.update_data(event_details=event_details)
    await wizard_regenerate_after_field_change(message, state)



@create_content_wizard.callback_query(F.data == "narrative_official", ContentWizard.waiting_for_wizard_narrative_style_edit)
async def wizard_update_narrative_official_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(narrative_style="📋 Официально-деловой стиль")
    await wizard_regenerate_after_field_change(callback.message, state)







async def wizard_regenerate_after_field_change(message, state: FSMContext):
    """Перегенерация текста после изменения поля."""
    await message.answer(
        "🔄 **Перегенерируем текст с новыми параметрами...**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await wizard_start_text_generation(message, state)


# ===== ЭТАП 3: РАБОТА С ИЗОБРАЖЕНИЕМ =====

@create_content_wizard.callback_query(F.data == "wizard_image_ai")
async def wizard_image_ai_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора генерации ИИ изображения."""
    await callback.answer()
    await state.update_data(image_source="🤖 Сгенерировать ИИ")

    await callback.message.answer(
        "🎨 **Описание изображения**\n\n"
        "Опишите, какое изображение создать для поста:\n\n"
        "_Например: «Команда волонтеров помогает пожилым людям»_",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_image_prompt)


@create_content_wizard.callback_query(F.data == "wizard_image_upload")
async def wizard_image_upload_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора загрузки пользовательского фото."""
    await callback.answer()
    await state.update_data(image_source="📎 Загрузить своё")

    await callback.message.answer(
        "📎 **Загрузите ваше изображение**\n\n"
        "Пришлите фотографию, которую хотите использовать в посте.\n"
        "Поддерживаемые форматы: JPEG, PNG.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_image_user_upload)

WIZARD_FINAL_CONFIRM_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Создать контент", callback_data="wizard_create_content")],
        [InlineKeyboardButton(text="🔄 Изменить настройки", callback_data="wizard_modify_settings")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="wizard_back_to_image")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="wizard_back_to_main")]
    ]
)


@create_content_wizard.callback_query(F.data == "wizard_image_none")
async def wizard_image_none_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора без изображения."""
    await callback.answer()
    await state.update_data(image_source="🚫 Без фото")

    await callback.message.answer(
        "✅ **Выбрано: Без фото**\n\n"
        "**Готово к финальной генерации контента?**",
        reply_markup=WIZARD_FINAL_CONFIRM_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_final_confirm)


# ===== ОБРАБОТКА ПРОМПТА ИЗОБРАЖЕНИЯ =====

WIZARD_CONTENT_GENERATION_IMAGE_PROMPT_PREVIEW_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перегенерировать промпт", callback_data="wizard_prompt_regenerate")],
        [InlineKeyboardButton(text="✏️ Изменить промпт", callback_data="wizard_prompt_edit")],
        [InlineKeyboardButton(text="✅ Сгенерировать изображение", callback_data="wizard_generate_image")],
        [InlineKeyboardButton(text="⬅️ К источнику изображения", callback_data="wizard_back_to_image_source")]
    ]
)


@create_content_wizard.message(ContentWizard.waiting_for_wizard_image_prompt, F.text)
async def wizard_image_prompt_handler(message: Message, state: FSMContext):
    """Обработка описания изображения."""
    image_prompt = message.text.strip()
    await state.update_data(image_prompt=image_prompt)

    # Используем ИИ для улучшения промпта
    await message.answer(
        "🧠 **Улучшаем промпт с помощью ИИ...**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Получаем сервис генерации текста для улучшения промпта
        text_generation_service: TextGenerationService = dispatcher["text_content_generation_service"]
        card_generation_service: CardGenerationService = dispatcher["card_generation_service"]

        # Системный промпт для улучшения промпта изображений
        system_prompt = (
            "Ты — эксперт по созданию промптов для генерации изображений ИИ. "
            "Твоя задача — улучшить пользовательский промпт на русском языке, "
            "сделав его более детализированным и эффективным для создания качественных изображений. "
            "Добавь детали о стиле, освещении, композиции, цветах. "
            "Результат должен быть на русском языке, коротким (1-2 предложения), "
            "и подходящим для социальных сетей НКО. "
            "Ответь только улучшенным промптом, без дополнительных комментариев."
            "Примеры хороших промптов по теме поста:"
            "(Пост о защите животных) Промпт: 'Котики играют на мягком ковре, теплое освещение, забота, уют.'"
            "(Пост о пожилых людях) Промпт: 'Несколько пожилых людей гуляют по парку осенью. "
            "Нет искажения лиц, нет артифактов, реалистичность.'"
        )

        # Пользовательский промпт для улучшения
        user_prompt = f"Улучши этот промпт для генерации изображения: {image_prompt}"

        # Вызываем GPT для улучшения промпта
        logger.info(f"Начинаю улучшение промпта: '{image_prompt}'")

        # FIXME: улучши промпт
        enhanced_prompt = await card_generation_service.enhance_prompt(user_prompt, system_prompt)

        # Сохраняем улучшенный промпт
        await state.update_data(enhanced_image_prompt=enhanced_prompt)

        logger.info(f"Промпт улучшен: '{image_prompt}' -> '{enhanced_prompt}'")

        await message.answer(
            "✅ **Улучшенный промпт готов:**\n\n"
            f"```\n{enhanced_prompt}\n```\n\n"
            "**Что делать с промптом?**",
            reply_markup=WIZARD_CONTENT_GENERATION_IMAGE_PROMPT_PREVIEW_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.update_data(enhanced_image_prompt=enhanced_prompt)
        await state.set_state(ContentWizard.waiting_for_wizard_image_prompt_edit)

    except Exception as e:
        logger.exception(f"Ошибка улучшения промпта: {e}")
        await message.answer(
            "⚠️ Не удалось улучшить промпт. Продолжаем с оригиналом.",
            reply_markup=WIZARD_CONTENT_GENERATION_IMAGE_PROMPT_PREVIEW_KEYBOARD,
        )
        await state.set_state(ContentWizard.waiting_for_wizard_image_prompt_edit)


@create_content_wizard.callback_query(F.data == "wizard_prompt_regenerate")
async def wizard_prompt_regenerate_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик перегенерации промпта."""
    await callback.answer()

    await callback.message.answer(
        "🎨 **Новое описание изображения**\n\n"
        "Опишите изображение заново:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_image_prompt)


@create_content_wizard.callback_query(F.data == "wizard_prompt_edit")
async def wizard_prompt_edit_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик редактирования промпта."""
    await callback.answer()

    await callback.message.answer(
        "✏️ **Редактирование промпта**\n\n"
        "Введите новый промпт или укажите, что именно изменить в текущем:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_image_prompt_edit)


WIZARD_IMAGE_MANAGEMENT_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="wizard_image_regenerate")],
        [InlineKeyboardButton(text="✏️ Изменить промпт", callback_data="wizard_image_edit_prompt")],
        [InlineKeyboardButton(text="🎨 Генерация карточки", callback_data="wizard_create_content")],
        [InlineKeyboardButton(text="⬅️ К тексту", callback_data="wizard_back_to_text")],
        [InlineKeyboardButton(text="↩️ К источнику", callback_data="wizard_back_to_image_source")]
    ]
)


@create_content_wizard.callback_query(F.data == "wizard_generate_image")
async def wizard_generate_image_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик генерации изображения."""
    await callback.answer()

    from bot.handlers import IMAGE_GENERATION_PHOTO

    await callback.message.answer_photo(
        photo=IMAGE_GENERATION_PHOTO,
        caption="🎨 **Генерируем изображение...**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        data = await state.get_data()
        image_prompt = data.get("enhanced_image_prompt", data.get("image_prompt", ""))

        image_generation_service = dispatcher.get("image_generation_service")
        if not image_generation_service:
            raise Exception("Сервис генерации изображений не настроен")

        generated_image = await image_generation_service.generate_image(
            prompt=image_prompt,
            width=1024,
            height=768
        )

        await state.update_data(generated_image=generated_image)

        from aiogram.types.input_file import BufferedInputFile
        await callback.message.answer_photo(
            photo=BufferedInputFile(generated_image, "wizard_generated_image.png"),
            caption="✅ **Изображение готово!**\n\n**Что делать дальше?**",
            reply_markup=WIZARD_IMAGE_MANAGEMENT_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN
        )
        await state.set_state(ContentWizard.waiting_for_wizard_image_result)

    except Exception as e:
        logger.exception(f"Ошибка генерации изображения: {e}")
        await callback.message.answer(
            "❌ Ошибка генерации изображения. Попробуйте заново.",
            reply_markup=WIZARD_IMAGE_SOURCE_KEYBOARD,
        )
        await state.set_state(ContentWizard.waiting_for_wizard_image_source)


# ===== ОБРАБОТКА ЗАГРУЗКИ ПОЛЬЗОВАТЕЛЬСКОГО ИЗОБРАЖЕНИЯ =====

@create_content_wizard.message(ContentWizard.waiting_for_wizard_image_user_upload, F.photo)
async def wizard_user_image_handler(message: Message, state: FSMContext):
    """Обработчик загрузки пользовательского фото."""
    if not message.photo:
        await message.answer("Пожалуйста, загрузите изображение.")
        return

    photo = message.photo[-1]

    try:
        image_file = await bot.download(photo.file_id, destination=None)
        image_bytes = image_file.read()

        await state.update_data(user_image=image_bytes)
 
        await message.answer(
            "✅ **Изображение загружено!**\n\n"
            "**Готово к финальной генерации контента?**",
            reply_markup=WIZARD_FINAL_CONFIRM_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentWizard.waiting_for_wizard_final_confirm)

    except Exception as e:
        logger.exception(f"Ошибка загрузки изображения: {e}")
        await message.answer(
            "❌ Ошибка загрузки изображения. Попробуйте снова.",
            reply_markup=ReplyKeyboardRemove(),
        )


@create_content_wizard.message(ContentWizard.waiting_for_wizard_image_user_upload, F.document)
async def wizard_user_document_handler(message: Message, state: FSMContext):
    """Обработчик загрузки пользовательского документа с изображением."""
    if not message.document:
        return

    mime_type = message.document.mime_type
    if not mime_type or not mime_type.startswith('image/'):
        await message.answer("Пожалуйста, отправьте файл с изображением.")
        return

    try:
        document_file = await bot.download(message.document.file_id, destination=None)
        image_bytes = document_file.read()

        await state.update_data(user_image=image_bytes)

        await message.answer(
            "✅ **Изображение загружено!**\n\n"
            "**Готово к финальной генерации контента?**",
            reply_markup=WIZARD_FINAL_CONFIRM_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(ContentWizard.waiting_for_wizard_final_confirm)

    except Exception as e:
        logger.exception(f"Ошибка загрузки документа: {e}")
        await message.answer(
            "❌ Ошибка загрузки изображения. Попробуйте снова.",
            reply_markup=ReplyKeyboardRemove(),
        )


# ===== УПРАВЛЕНИЕ СГЕНЕРИРОВАННЫМ ИЗОБРАЖЕНИЕМ =====

@create_content_wizard.callback_query(F.data == "wizard_image_regenerate")
async def wizard_image_regenerate_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик перегенерации изображения."""
    await callback.answer()
    await wizard_generate_image_handler(callback, state)


@create_content_wizard.callback_query(F.data == "wizard_image_edit_prompt")
async def wizard_image_edit_prompt_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик редактирования промпта изображения."""
    await callback.answer()
    await callback.message.answer(
        "✏️ **Изменение промпта**\n\n"
        "Опишите новые параметры для изображения:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ContentWizard.waiting_for_wizard_image_prompt)


@create_content_wizard.callback_query(F.data == "wizard_finish")
async def wizard_finish_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик завершения Wizard."""
    await callback.answer()

    await callback.message.answer(
        "🎉 **Готово к финальной генерации контента!**\n\n"
        "Нажмите кнопку ниже для создания финального поста и карточек.",
        reply_markup=WIZARD_FINAL_CONFIRM_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_final_confirm)


# ===== ЭТАП 4: ФИНАЛЬНОЕ ЗАВЕРШЕНИЕ =====

@create_content_wizard.callback_query(F.data == "wizard_back_to_image_source")
async def wizard_back_to_image_source_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору источника изображения."""
    await callback.answer()

    await callback.message.answer(
        "🖼️ **Выберите источник изображения:**",
        reply_markup=WIZARD_IMAGE_SOURCE_KEYBOARD,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_image_source)


@create_content_wizard.callback_query(F.data == "wizard_back_to_text")
async def wizard_back_to_text_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к результату генерации текста."""
    await callback.answer()

    data = await state.get_data()
    generated_text = data.get("generated_text", "")

    await callback.message.answer(
        "✅ **Текст поста:**\n\n"
        f"{generated_text}\n\n"
        "**Что делать с текстом?**",
        reply_markup=WIZARD_CONTENT_GENERATION_MANAGEMENT_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_text_result)


@create_content_wizard.callback_query(F.data == "wizard_modify_settings")
async def wizard_modify_settings_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик модификации настроек."""
    await callback.answer()

    await callback.message.answer(
        "⚙️ **Модификация настроек**\n\n"
        "Возврат к этапу настройки параметров. Что хотите изменить?",
        reply_markup=WIZARD_CONTENT_GENERATION_FIELD_SELECT_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_field_select)


WIZARD_CARD_READY_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перегенерировать карточки", callback_data="wizard_regenerate_card")],
        [InlineKeyboardButton(text="✏️ Изменить текст карточки", callback_data="wizard_edit_card_text")],
        [InlineKeyboardButton(text="📝 Написать промпт для карточки", callback_data="wizard_write_card_prompt")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="wizard_back_to_main")]
    ]
)


@create_content_wizard.callback_query(F.data == "wizard_back_to_image")
async def wizard_back_to_image_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к этапу работы с изображением."""
    await callback.answer()

    await callback.message.answer(
        "🖼️ **Выберите источник изображения:**",
        reply_markup=WIZARD_IMAGE_SOURCE_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_image_source)


@create_content_wizard.callback_query(F.data == "wizard_create_content")
async def wizard_create_content_handler(callback: CallbackQuery, state: FSMContext):
    """Финальная генерация только карточек (текст уже готов)."""
    await callback.answer()

    from bot.handlers import CARD_GENERATION_PHOTO

    await callback.message.answer_photo(
        photo=CARD_GENERATION_PHOTO,
        content="🎨 **Создаем информационные карточки...**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Получаем сохраненные данные из Wizard
        data = await state.get_data()
        generated_text = data.get("generated_text", "")
        platform = data.get("platform", "📱 ВКонтакте (для молодежи)")

        # Получаем информацию об НКО из базы данных
        ngo_service = dispatcher["ngo_service"]
        user_id = callback.from_user.id
        ngo_data = ngo_service.get_ngo_data_by_user_id(user_id)

        # Устанавливаем значения по умолчанию
        ngo_name = ngo_data.get("ngo_name", "Ваша НКО") if ngo_data else "Ваша НКО"
        ngo_contact = ngo_data.get("ngo_contact", "тел: +7 (XXX) XXX-XX-XX") if ngo_data else "тел: +7 (XXX) XXX-XX-XX"

        # Получаем изображение (уже должно быть сгенерировано на предыдущих этапах)
        generated_image = None
        image_source = data.get("image_source", "")
        if image_source == "🤖 Сгенерировать ИИ":
            generated_image = data.get("generated_image")
        elif image_source == "📎 Загрузить своё":
            generated_image = data.get("user_image")

        # Определяем подзаголовок в зависимости от режима
        wizard_mode = data.get("wizard_mode", "structured")
        if wizard_mode == "structured":
            subtitle = f"Событие: {data.get('event_type', 'мероприятие')}"
        else:
            subtitle = f"Для {data.get('event_audience', 'наших подопечных')}"

        # Создаем краткий контент для карточки
        await callback.message.answer(
            "🤖 Создаю краткий контент для карточки...",
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            # Генерируем сокращенный контент специально для карточки
            card_text_generation_service: TextGenerationService = dispatcher["text_content_generation_service"]
            card_generation_service: CardGenerationService = dispatcher["card_generation_service"]
            card_content = await card_generation_service.generate_card_text(data, generated_text)

            # Используем сгенерированный сокращенный контент, если он получился подходящим
            if card_content and len(card_content.strip()) > 10 and len(card_content.strip()) < 300:
                card_content_for_template = card_content.strip()
                logger.info(f"Используем сокращенный контент для карточки: {len(card_content)} символов")
            else:
                # Fallback - обрезаем текст
                card_content_for_template = f"{generated_text[:300]}..." if len(generated_text) > 300 else generated_text
                logger.warning(f"GPT дал неподходящий контент ({len(card_content) if card_content else 0} символов), используем fallback")

            await callback.message.answer(
                "✅ Краткий контент для карточки готов!",
                reply_markup=ReplyKeyboardRemove(),
            )

        except Exception as e:
            logger.exception("Ошибка генерации сокращенного контента для карточки, используем fallback")
            # Fallback в случае ошибки
            card_content_for_template = f"{generated_text[:300]}..." if len(generated_text) > 300 else generated_text

        # Генерируем заголовок для карточки на основе текста
        await callback.message.answer(
            "🏷️ Создаю заголовок для карточки...",
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            # Используем GPT для генерации привлекательного заголовка
            title_generation_prompt = (
                f"Исходный текст поста: {card_content_for_template}\n\n"
                "Создай короткий, привлекательный заголовок (5-7 слов) для информационной карточки НКО. "
                "Заголовок должен быть ярким, мотивирующим и побуждать к участию. "
                "Не добавляй кавычки в ответе."
            )

            title = await card_text_generation_service.generate_text(title_generation_prompt, title_generation_prompt)

            # Очищаем и ограничиваем длину заголовка
            if title:
                title = title.strip()
                if len(title) > 50:  # Ограничиваем длину
                    title = title[:47] + "..."
            else:
                # Fallback если GPT не сгенерировал заголовок
                title = data.get('event_type', 'Событие НКО')[:30] + "..."

            await callback.message.answer(
                f"✅ Заголовок готов: **{title}**",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.MARKDOWN,
            )

        except Exception as e:
            logger.exception("Ошибка генерации заголовка для карточки, используем fallback")
            # Fallback заголовок
            title = data.get('event_type', 'Событие НКО')[:30] + "..."
            if len(title) <= 3 or title == "...":  # Если получился слишком короткий
                title = "Присоединяйтесь к событию!"

        # Подготавливаем данные для генерации карточек



        template_data = {
            "title": title,
            "subtitle": subtitle or "",
            "content": card_content_for_template,
            "org_name": ngo_name or "Ваша НКО",
            "contact_info": ngo_contact or "",
            "text_color": "#333333",
        }

        # Добавляем специфические данные для структурированной формы
        if wizard_mode == "structured":
            template_data.update({
                "event_type": data['event_type'],
                "event_date": data['event_date'],
                "event_place": data['event_place'],
                "event_audience": data['event_audience'],
                "event_details": data['event_details'],
                "narrative_style": data['narrative_style'],
            })

        # Добавляем данные для свободной формы
        if wizard_mode == "free_form":
            template_data.update({
                "user_description": data['user_description'],
                "narrative_style": data['narrative_style'],
            })

        # Добавляем изображение для фона карточки
        if generated_image:
            template_data["background_image_bytes"] = generated_image
            logger.info(f"Фоновое изображение добавлено: {len(generated_image)} байт")


        card_generation_service: CardGenerationService = dispatcher["card_generation_service"]


        card = await card_generation_service.generate_card(
            parameters,
            data
        )


        await callback.message.answer(
            "🎨 Вот ваша карточка для соцсетей:",
            reply_markup=ReplyKeyboardRemove(),
        )

        await callback.message.answer_photo(
            photo=BufferedInputFile(card, f"wizard_card.png"),
            # caption=caption,
            reply_markup=ReplyKeyboardRemove(),
        )

        # Показываем сгенерированный текст и завершаем Wizard
        await callback.message.answer(
            "📝 **Ваш сгенерированный текст:**",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await callback.message.answer(
            generated_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardRemove(),
        )

        await callback.message.answer(
            "✨ Все материалы готовы к публикации!",
            reply_markup=WIZARD_CARD_READY_KEYBOARD,
        )

        await state.clear()  # Очищаем состояние после успешного завершения

    except Exception as e:
        logger.exception(f"Ошибка генерации карточек в Wizard: {e}")
        await callback.message.answer(
            "❌ Ошибка создания карточек. Попробуйте снова.",
            reply_markup=WIZARD_FINAL_CONFIRM_KEYBOARD,
        )


# ===== ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ПРОМПТА =====

@create_content_wizard.message(ContentWizard.waiting_for_wizard_image_prompt_edit, F.text)
async def wizard_image_prompt_edit_handler(message: Message, state: FSMContext):
    """Обработка редактирования промпта."""
    old_prompt = await state.get_value("enhanced_prompt")
    new_prompt = message.text.strip()

    # Получаем сервис генерации текста для улучшения промпта
    text_generation_service = dispatcher["text_content_generation_service"]

    # Системный промпт для улучшения промпта изображений
    system_prompt = (
        "Ты — эксперт по созданию промптов для генерации изображений ИИ. "
        "Твоя задача — улучшить пользовательский промпт на русском языке, "
        "сделав его более детализированным и эффективным для создания качественных изображений. "
        "Добавь детали о стиле, освещении, композиции, цветах. "
        "Результат должен быть на русском языке, коротким (1-2 предложения), "
        "и подходящим для социальных сетей НКО. "
        "Ответь только улучшенным промптом, без дополнительных комментариев."
        "Примеры хороших промптов по теме поста:"
        "(Пост о защите животных) Промпт: 'Котики играют на мягком ковре, теплое освещение, забота, уют.'"
        "(Пост о пожилых людях) Промпт: 'Несколько пожилых людей гуляют по парку осенью. "
        "Нет искажения лиц, нет артифактов, реалистичность.'"
    )

    # Пользовательский промпт для улучшения
    user_prompt = (f"Учитывая эти указания: {new_prompt}, "
                   f"улучши данный промпт для генерации изображения: {old_prompt}")

    # Вызываем GPT для улучшения промпта
    logger.info(f"Начинаю улучшение промпта: '{old_prompt}'")
    raw_response = await text_generation_service.gpt_client.generate(user_prompt, system_prompt)
    enhanced_prompt = text_generation_service.response_processor.process_response(raw_response)

    await state.update_data(enhanced_image_prompt=enhanced_prompt)

    await message.answer(
        "✅ **Обновленный промпт:**\n\n"
        f"```\n{enhanced_prompt}\n```\n\n"
        "**Что делать с промптом?**",
        reply_markup=WIZARD_CONTENT_GENERATION_IMAGE_PROMPT_PREVIEW_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )


# ===== ОБРАБОТЧИКИ НАВИГАЦИИ =====

@create_content_wizard.callback_query(F.data == "wizard_back_to_setup")
async def wizard_back_to_setup_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат к началу настройки."""
    await callback.answer()
    await state.set_state(ContentWizard.waiting_for_wizard_mode)

    await callback.message.answer(
        "🔙 Возвращаемся к выбору формы:",
        reply_markup=CONTENT_WIZARD_SELECT_MODE_KEYBOARD,
    )


# ===== ОБРАБОТЧИКИ КОМПЛЕКТАЦИИ КАРТОЧЕК =====

@create_content_wizard.callback_query(F.data == "wizard_regenerate_card")
async def wizard_regenerate_card_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик перегенерации карточек."""
    await callback.answer()

    await callback.message.answer(
        "🔄 **Перегенерируем карточки...**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
    )

    # Получаем сохраненные данные и перезапускаем генерацию карточек
    data = await state.get_data()
    if not data.get("generated_text"):
        await callback.message.answer(
            "❌ Ошибка: текст не найден. Попробуйте создать контент заново.",
        )
        return

    # Перезапускаем финальную генерацию
    await wizard_create_content_handler(callback, state)


@create_content_wizard.callback_query(F.data == "wizard_edit_card_text")
async def wizard_edit_card_text_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик редактирования текста карточки."""
    await callback.answer()

    await callback.message.answer(
        "📝 **Редактирование текста карточки**\n\n"
        "Опишите, как нужно изменить текст на карточке:\n\n"
        "_Например: «Сократи текст», «Измени стиль», «Добавь больше призывов к действию»_",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_card_text_edit)


@create_content_wizard.callback_query(F.data == "wizard_write_card_prompt")
async def wizard_write_card_prompt_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик написания промпта для текста карточки."""
    await callback.answer()

    await callback.message.answer(
        "📝 **Создание промпта для текста карточки**\n\n"
        "Опишите, какой текст должен быть на карточке:\n\n"
        "_Например: «Сделай текст очень коротким, только суть события и контакты»_",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentWizard.waiting_for_wizard_card_prompt)


# ===== ОБРАБОТКА РЕДАКТИРОВАНИЯ ТЕКСТА КАРТОЧКИ =====

@create_content_wizard.message(ContentWizard.waiting_for_wizard_card_text_edit, F.text)
async def wizard_update_card_text_handler(message: Message, state: FSMContext):
    """Обработка редактирования текста карточки."""
    edit_instruction = message.text.strip()
    await state.update_data(card_text_edit_instruction=edit_instruction)

    await message.answer(
        "✏️ **Обновляем текст карточки...**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        # Получаем текущий сгенерированный текст
        data = await state.get_data()
        current_text = data.get("generated_text", "")

        # Используем text_editing сервис для редактирования
        from services.text_editing import TextEditingService
        editing_service = TextEditingService()

        # Генерируем краткий текст специально для карточки с учетом инструкции
        edited_card_text = await editing_service.edit_text(
            text=current_text,
            instructions=f"Создай краткий текст (до 300 символов) для карточки НКО: {edit_instruction}"
        )

        await state.update_data(card_custom_text=edited_card_text)

        await message.answer(
            "✅ **Текст карточки обновлен:*\n\n"
            f"{edited_card_text}\n\n"
            "🔄 **Перегенерируем карточки с новым текстом...**",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Перезапускаем генерацию карточек с новым текстом
        await wizard_regenerate_card_from_text(message, state, edited_card_text)

    except Exception as e:
        logger.exception(f"Ошибка редактирования текста карточки: {e}")
        await message.answer(
            "❌ Ошибка редактирования текста карточки. Попробуем перегенерировать.",
        )
        await wizard_regenerate_card_handler_from_message(message, state)


# ===== ОБРАБОТКА ПРОМПТА ДЛЯ ТЕКСТА КАРТОЧКИ =====

@create_content_wizard.message(ContentWizard.waiting_for_wizard_card_prompt, F.text)
async def wizard_generate_card_from_prompt_handler(message: Message, state: FSMContext):
    """Обработка промпта для создания текста карточки."""
    card_prompt = message.text.strip()
    await state.update_data(card_text_prompt=card_prompt)

    await message.answer(
        "🤖 **Создаю текст для карточки по вашему промпту...**",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        # Генерируем новый текст для карточки на основе промпта
        text_generation_service: TextGenerationService = dispatcher["text_content_generation_service"]

        # Получаем данные из state
        data = await state.get_data()
        original_text = data.get("generated_text", "")

        # Создаем промпт для генерации текста карточки
        card_generation_prompt = (
            f"Исходный текст: {original_text[:500]}...\n\n"
            f"Задача: {card_prompt}\n\n"
            "Создай краткий текст (до 300 символов) для информационной карточки НКО."
        )

        card_text = await text_generation_service.generate_text(card_generation_prompt, card_generation_prompt)

        if card_text and len(card_text.strip()) > 10 and len(card_text.strip()) < 300:
            await state.update_data(card_custom_text=card_text.strip())

            await message.answer(
                "✅ **Текст для карточки создан:*\n\n"
                f"{card_text}\n\n"
                "🔄 **Перегенерируем карточки с новым текстом...**",
                parse_mode=ParseMode.MARKDOWN,
            )

            # Перезапускаем генерацию карточек с новым текстом
            await wizard_regenerate_card_from_text(message, state, card_text.strip())
        else:
            await message.answer(
                "⚠️ **Созданный текст не подходит для карточки. Попробуйте другой промпт.**",
                reply_markup=WIZARD_CARD_READY_KEYBOARD,
            )

    except Exception as e:
        logger.exception(f"Ошибка генерации текста карточки по промпту: {e}")
        await message.answer(
            "❌ Ошибка создания текста карточки. Попробуйте перегенерацию.",
        )
        await wizard_regenerate_card_handler_from_message(message, state)


async def wizard_regenerate_card_from_text(message: Message, state: FSMContext, card_text: str):
    """Перегенерация карточек с указанным текстом."""
    try:
        # Получаем сохраненные данные из Wizard
        data = await state.get_data()
        platform = data.get("platform", "📱 ВКонтакте (для молодежи)")

        # Получаем информацию об НКО из базы данных
        ngo_service: TextGenerationService = dispatcher["ngo_service"]
        user_id = message.from_user.id
        ngo_data = ngo_service.get_ngo_data_by_user_id(user_id)

        # Устанавливаем значения по умолчанию
        ngo_name = ngo_data.get("ngo_name", "Ваша НКО") if ngo_data else "Ваша НКО"
        ngo_contact = ngo_data.get("ngo_contact", "тел: +7 (XXX) XXX-XX-XX") if ngo_data else "тел: +7 (XXX) XXX-XX-XX"

        # Получаем изображение
        generated_image = None
        image_source = data.get("image_source", "")
        if image_source == "🤖 Сгенерировать ИИ":
            generated_image = data.get("generated_image")
        elif image_source == "📎 Загрузить своё":
            generated_image = data.get("user_image")

        # Определяем подзаголовок в зависимости от режима
        wizard_mode = data.get("wizard_mode", "structured")
        if wizard_mode == "structured":
            subtitle = f"Событие: {data.get('event_type', 'мероприятие')}"
        else:
            subtitle = f"Для {data.get('event_audience', 'наших подопечных')}"

        # Генерируем заголовок для карточки на основе текста
        await message.answer(
            "🏷️ Создаю заголовок для карточки...",
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            # Используем GPT для генерации привлекательного заголовка
            title_generation_prompt = (
                f"Исходный текст поста: {card_text}\n\n"
                "Создай короткий, привлекательный заголовок (5-7 слов) для информационной карточки НКО. "
                "Заголовок должен быть ярким, мотивирующим и побуждать к участию. "
                "Не добавляй кавычки в ответе."
            )

            title = await card_text_generation_service.generate_text(title_generation_prompt, title_generation_prompt)

            # Очищаем и ограничиваем длину заголовка
            if title:
                title = title.strip()
                if len(title) > 50:  # Ограничиваем длину
                    title = title[:47] + "..."
            else:
                # Fallback если GPT не сгенерировал заголовок
                title = data.get('event_type', 'Событие НКО')[:30] + "..."

            await message.answer(
                f"✅ Заголовок готов: **{title}**",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.MARKDOWN,
            )

        except Exception as e:
            logger.exception("Ошибка генерации заголовка для карточки, используем fallback")
            # Fallback заголовок
            title = data.get('event_type', 'Событие НКО')[:30] + "..."
            if len(title) <= 3 or title == "...":  # Если получился слишком короткий
                title = "Присоединяйтесь к событию!"

        # Подготавливаем данные для генерации карточек


        goal = "🎯 Рассказать о мероприятии"
        template_data = {
            "title": title,
            "subtitle": subtitle or "",
            "content": card_text,  # Используем переданный кастомный текст
            "org_name": ngo_name or "Ваша НКО",
            "contact_info": ngo_contact or "",
            "secondary_color": get_secondary_color_by_goal(goal) or "#764ba2",
            "text_color": "#333333",
            "background_color": "#f5f7fa",
        }

        # Добавляем специфические данные для структурированной формы
        if wizard_mode == "structured":
            template_data.update({
                "event_type": data.get('event_type', ''),
                "event_date": data.get('event_date', ''),
                "event_place": data.get('event_place', ''),
                "event_audience": data.get('event_audience', ''),
                "event_details": data.get('event_details', ''),
                "narrative_style": data.get('narrative_style', ''),
            })

        # Добавляем данные для свободной формы
        if wizard_mode == "free_form":
            template_data.update({
                "user_description": data.get('user_description', ''),
                "narrative_style": data.get('narrative_style', ''),
            })

        # Добавляем изображение для фона карточки
        if generated_image:
            template_data["background_image_bytes"] = generated_image

        from services.card_generation import CardGenerationService
        card_generation_service: CardGenerationService = Dispatcher["card_generation_service"]

        card = await card_generation_service.generate_card(
            parameters,
            data,
        )

        await message.answer(
            "🎨 **Обновленные карточки для соцсетей:**",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )

        await message.answer_photo(
            photo=BufferedInputFile(card, f"updated_wizard_card.png"),
            # caption=caption,
            reply_markup=ReplyKeyboardRemove(),
        )

        await message.answer(
            "✨ **Обновленные материалы готовы к публикации!**",
            reply_markup=WIZARD_CARD_READY_KEYBOARD,
        )

    except Exception as e:
        logger.exception(f"Ошибка перегенерации карточек: {e}")
        await message.answer(
            "❌ Ошибка создания обновленных карточек. Попробуйте снова.",
            reply_markup=WIZARD_CARD_READY_KEYBOARD,
        )


async def wizard_regenerate_card_handler_from_message(message: Message, state: FSMContext):
    """Перегенерация карточек из message handler'а."""
    await message.answer(
        "🔄 **Перегенерируем карточки...**",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Получаем сохраненные данные из Wizard
        data = await state.get_data()
        generated_text = data.get("generated_text", "")
        platform = data.get("platform", "📱 ВКонтакте (для молодежи)")

        # Получаем информацию об НКО из базы данных
        ngo_service = dispatcher["ngo_service"]
        user_id = message.from_user.id
        ngo_data = ngo_service.get_ngo_data_by_user_id(user_id)

        # Устанавливаем значения по умолчанию
        ngo_name = ngo_data.get("ngo_name", "Ваша НКО") if ngo_data else "Ваша НКО"
        ngo_contact = ngo_data.get("ngo_contact", "тел: +7 (XXX) XXX-XX-XX") if ngo_data else "тел: +7 (XXX) XXX-XX-XX"

        # Получаем изображение (уже должно быть сгенерировано на предыдущих этапах)
        generated_image = None
        image_source = data.get("image_source", "")
        if image_source == "🤖 Сгенерировать ИИ":
            generated_image = data.get("generated_image")
        elif image_source == "📎 Загрузить своё":
            generated_image = data.get("user_image")

        # Определяем подзаголовок в зависимости от режима
        wizard_mode = data.get("wizard_mode", "structured")
        if wizard_mode == "structured":
            subtitle = f"Событие: {data.get('event_type', 'мероприятие')}"
        else:
            subtitle = f"Для {data.get('event_audience', 'наших подопечных')}"

        # Создаем краткий контент для карточки
        await message.answer(
            "🤖 Создаю краткий контент для карточки...",
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            # Генерируем сокращенный контент специально для карточки
            card_text_generation_service: TextGenerationService = dispatcher["text_content_generation_service"]
            card_content = await card_text_generation_service.generate_card_text(data, generated_text)

            # Используем сгенерированный сокращенный контент, если он получился подходящим
            if card_content and len(card_content.strip()) > 10 and len(card_content.strip()) < 300:
                card_content_for_template = card_content.strip()
                logger.info(f"Используем сокращенный контент для карточки: {len(card_content)} символов")
            else:
                # Fallback - обрезаем текст
                card_content_for_template = f"{generated_text[:300]}..." if len(generated_text) > 300 else generated_text
                logger.warning(f"GPT дал неподходящий контент ({len(card_content) if card_content else 0} символов), используем fallback")

            await message.answer(
                "✅ Краткий контент для карточки готов!",
                reply_markup=ReplyKeyboardRemove(),
            )

        except Exception as e:
            logger.exception("Ошибка генерации сокращенного контента для карточки, используем fallback")
            # Fallback в случае ошибки
            card_content_for_template = f"{generated_text[:300]}..." if len(generated_text) > 300 else generated_text

        # Генерируем заголовок для карточки на основе текста
        await message.answer(
            "🏷️ Создаю заголовок для карточки...",
            reply_markup=ReplyKeyboardRemove(),
        )

        try:
            # Используем GPT для генерации привлекательного заголовка
            title_generation_prompt = (
                f"Исходный текст поста: {card_content_for_template}\n\n"
                "Создай короткий, привлекательный заголовок (5-7 слов) для информационной карточки НКО. "
                "Заголовок должен быть ярким, мотивирующим и побуждать к участию. "
                "Не добавляй кавычки в ответе."
            )

            title = await card_text_generation_service.generate_text(title_generation_prompt, title_generation_prompt)

            # Очищаем и ограничиваем длину заголовка
            if title:
                title = title.strip()
                if len(title) > 50:  # Ограничиваем длину
                    title = title[:47] + "..."
            else:
                # Fallback если GPT не сгенерировал заголовок
                title = data.get('event_type', 'Событие НКО')[:30] + "..."

            await message.answer(
                f"✅ Заголовок готов: **{title}**",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.MARKDOWN,
            )

        except Exception as e:
            logger.exception("Ошибка генерации заголовка для карточки, используем fallback")
            # Fallback заголовок
            title = data.get('event_type', 'Событие НКО')[:30] + "..."
            if len(title) <= 3 or title == "...":  # Если получился слишком короткий
                title = "Присоединяйтесь к событию!"

        # Подготавливаем данные для генерации карточек
        from bot.utils import (
            get_title_by_goal,
            get_color_by_goal,
            get_secondary_color_by_goal,
            get_template_by_platform,
        )

        goal = "🎯 Рассказать о мероприятии"  # Можем получить из данных Wizard

        template_data = {
            "title": title,
            "subtitle": subtitle or "",
            "content": card_content_for_template,
            "org_name": ngo_name or "Ваша НКО",
            "contact_info": ngo_contact or "",
            "primary_color": get_color_by_goal(goal) or "#667eea",
            "secondary_color": get_secondary_color_by_goal(goal) or "#764ba2",
            "text_color": "#333333",
            "background_color": "#f5f7fa",
        }

        # Добавляем специфические данные для структурированной формы
        if wizard_mode == "structured":
            template_data.update({
                "event_type": data.get('event_type', ''),
                "event_date": data.get('event_date', ''),
                "event_place": data.get('event_place', ''),
                "event_audience": data.get('event_audience', ''),
                "event_details": data.get('event_details', ''),
                "narrative_style": data.get('narrative_style', ''),
            })

        # Добавляем данные для свободной формы
        if wizard_mode == "free_form":
            template_data.update({
                "user_description": data.get('user_description', ''),
                "narrative_style": data.get('narrative_style', ''),
            })

        # Добавляем изображение для фона карточки
        if generated_image:
            template_data["background_image_bytes"] = generated_image
            logger.info(f"Фоновое изображение добавлено: {len(generated_image)} байт")

        template_name = get_template_by_platform(platform)
        logger.info(f"Using template: {template_name} for platform: {platform}")

        card_generation_service: CardGenerationService = dispatcher["card_generation_service"]

        card = await card_generation_service.generate_card(
            parameters,
            data
        )


        # Отправляем сгенерированное изображение сначала отдельно (если есть)
        if generated_image and image_source == "🤖 Сгенерировать ИИ":
            await message.answer(
                "🖼️ **Ваше сгенерированное изображение:**",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.MARKDOWN,
            )
            from aiogram.types.input_file import BufferedInputFile
            await message.answer_photo(
                photo=BufferedInputFile(generated_image, "wizard_generated_image.png"),
                caption="🎨 Сгенерированное ИИ изображение",
                reply_markup=ReplyKeyboardRemove(),
            )


        await message.answer(
            "🎨 Вот ваши карточки для соцсетей:",
            reply_markup=ReplyKeyboardRemove(),
        )

        await message.answer_photo(
            photo=BufferedInputFile(card, f"wizard_card.png"),
            # caption=caption,
            reply_markup=ReplyKeyboardRemove(),
        )

        # Показываем сгенерированный текст
        await message.answer(
            "📝 **Ваш сгенерированный текст:**",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
        )
        await message.answer(
            generated_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardRemove(),
        )

        await message.answer(
            "✨ Все материалы готовы к публикации!",
            reply_markup=WIZARD_CARD_READY_KEYBOARD,
        )

    except Exception as e:
        logger.exception(f"Ошибка перегенерации карточек: {e}")
        await message.answer(
            "❌ Ошибка перегенерации карточек. Попробуйте снова.",
            reply_markup=WIZARD_CARD_READY_KEYBOARD,
        )


@create_content_wizard.callback_query(F.data == "create_again")
async def create_again_handler(callback: CallbackQuery, state: FSMContext):
    from bot.handlers.start import start_handler

    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


@create_content_wizard.callback_query(F.data == "get_tips")
async def get_tips_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    platform = data.get("platform", "")
    audience = ", ".join(data.get("audience", [])) or "не указана"
    goal = data.get("goal", "вашей задачи")

    tips_text = (
        "💡 Общие советы по продвижению:\n\n"
        "• Публикуйте регулярно, чтобы аудитория не забывала о вас\n"
        "• Комбинируйте информационный и эмоциональный контент\n"
        "• Задавайте вопросы в постах для повышения вовлечённости\n"
        "• Анализируйте статистику и корректируйте стратегию\n"
        "• Сотрудничайте с другими НКО для взаимного продвижения"
    )

    await callback.message.answer(
        f"Цель: {goal}\nАудитория: {audience}\nПлатформа: {platform or '—'}\n\n{tips_text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Создать ещё", callback_data="create_again")],
            ]
        ),
    )





