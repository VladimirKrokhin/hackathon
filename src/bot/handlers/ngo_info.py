"""
Обработчики для работы с данными об НКО через базу данных
"""
import logging

from aiogram import Router, F
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from bot import dispatcher
from bot.states import NGOInfo
from services.ngo_service import NGOService

from models import Ngo


ngo_info_router = Router(name="ngo_info")
logger = logging.getLogger(__name__)


NGO_DONE_CALLBACK = "ngo_done"

UPDATE_NGO_CONTENT_CALLBACK_DATA = "update_ngo"
VIEW_NGO_INFO_CALLBACK_DATA = "ngo_info"

BACK_TO_MAIN_MENU_CALLBACK_DATA = "back_to_main"

NGO_INFO_MENU_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Посмотреть мою НКО", callback_data="view_ngo")],
        [InlineKeyboardButton(text="🔄 Обновить данные НКО", callback_data=UPDATE_NGO_CONTENT_CALLBACK_DATA)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_MAIN_MENU_CALLBACK_DATA)],
    ]
)

NGO_BACK_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_MAIN_MENU_CALLBACK_DATA)],
    ]
)

FILL_NGO_INFO_CALLBACK_DATA = "fill_ngo"

NGO_INFO_MENU_KEYBOARD_NO_NGO = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Заполнить информацию об НКО", callback_data=FILL_NGO_INFO_CALLBACK_DATA)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=BACK_TO_MAIN_MENU_CALLBACK_DATA)],
    ]
)

# FIXME: этот обработчик используется
# FIXME: не сохраняет обновленные данные
@ngo_info_router.callback_query(F.data == UPDATE_NGO_CONTENT_CALLBACK_DATA)
async def update_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик обновления НКО."""
    await callback.answer()

    await state.clear()
    await state.set_state(NGOInfo.waiting_for_ngo_name)

    await callback.message.answer(
        "🔄 Обновление данных НКО\n\n"
        "Введите новое название НКО (или текущее, если не хотите менять):",
        reply_markup=NGO_CANCEL_KEYBOARD,
    )

# FIXME: этот обработчик используется
@ngo_info_router.message(NGOInfo.waiting_for_ngo_name, F.text)
async def ngo_name_handler(message: Message, state: FSMContext):
    """Обработчик ввода названия НКО."""
    text = message.text.strip()

    if not text:
        # TODO: подумай как это можно сделать через смену состояний на обратное
        await message.answer(
            "Пожалуйста, введите название вашей НКО.",
            reply_markup=NGO_NAVIGATION_KEYBOARD,
        )
        return

    await state.update_data(ngo_name=text)

    await message.answer(
        f"✅ Название: {text}\n\n"
        "📝 Теперь расскажите, чем занимается ваша НКО? (опишите основную деятельность, цели, задачи)\n\n"
        "Можете ввести подробное описание или нажать ⏩ Пропустить, если не хотите заполнять это поле.",
        reply_markup=NGO_NAVIGATION_KEYBOARD,
    )
    await state.set_state(NGOInfo.waiting_for_ngo_description)

# FIXME: Этот обработчик используется
@ngo_info_router.message(NGOInfo.waiting_for_ngo_description, F.text)
async def ngo_description_handler(message: Message, state: FSMContext):
    """Обработчик ввода описания НКО."""
    text = message.text.strip()
    description = text

    await state.update_data(ngo_description=description)

    await message.answer(
        f"✅ Описание: {description}\n\n"
        "🎯 Какие формы деятельности ведет ваша НКО? (например: благотворительность, просвещение, помощь животным и т.д.)\n\n"
        "Можете перечислить через запятую или нажать ⏩ Пропустить.",
        reply_markup=NGO_NAVIGATION_KEYBOARD,
    )
    await state.set_state(NGOInfo.waiting_for_ngo_activities)

# FIXME: Этот обработчик используется
@ngo_info_router.message(NGOInfo.waiting_for_ngo_activities, F.text)
async def ngo_activities_handler(message: Message, state: FSMContext):
    """Обработчик ввода форм деятельности НКО."""
    text = message.text.strip()
    activities = text

    await state.update_data(ngo_activities=activities)

    await message.answer(
        f"✅ Формы деятельности: {activities}\n\n"
        "📞 Укажите контактную информацию для связи (телефон, email, сайт или социальные сети)\n\n"
        "Можете указать любые удобные способы связи или нажать ⏩ Пропустить.",
        reply_markup=NGO_NAVIGATION_KEYBOARD,
    )
    await state.set_state(NGOInfo.waiting_for_ngo_contact)

# FIXME: Этот обработчик используется
@ngo_info_router.message(NGOInfo.waiting_for_ngo_contact, F.text)
async def ngo_contact_handler(message: Message, state: FSMContext):
    """Обработчик ввода контактной информации НКО."""
    text = message.text.strip()
    contact = text

    await state.update_data(ngo_contact=contact)

    # Показываем итоговую информацию для подтверждения
    data = await state.get_data()
    name = data["ngo_name"]
    description = data["ngo_description"]
    activities = data["ngo_activities"]
    contact_info = contact

    # TODO: переделай на CreateNgoDto
    ngo_info = Ngo(
        id_=None,
        user_id=message.from_user.id,
        name=name,
        description=description,
        activities=activities,
        contacts=contact_info
    )
    await state.update_data(
        {"ngo_info": ngo_info}
    )

    summary = (
        f"🏢 **Информация о НКО \"{name}\"**\n\n"
        f"📝 **Описание:** {description}\n\n"
        f"🎯 **Деятельность:** {activities}\n\n"
        f"📞 **Контакты:** {contact_info}\n\n"
        "Подтверждаете данные? Их можно будет изменить позже."
    )

    keyboard = NGO_BACK_KEYBOARD.inline_keyboard.append(
        [InlineKeyboardButton(text="✅ Готово", callback_data=NGO_DONE_CALLBACK)]
    )

    await message.answer(
        summary,
        # FIXME: оставь клавиатуру "Подтверить" или что-то другое...
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(NGOInfo.waiting_for_ngo_confirmation)


# Колбэки

def get_ngo_summary(ngo: Ngo) -> str:
    """
    Получить краткую сводку данных об НКО для отображения пользователю
    """
    try:
        summary = (
            f"🏢 **Информация о НКО \"{ngo.name}\"**\n\n"
            f"📝 **Описание:** {ngo.description}\n\n"
            f"🎯 **Деятельность:** {ngo.activities}\n\n"
            f"📞 **Контакты:** {ngo.contacts}\n\n"
        )
        return summary
    except Exception as e:
        logger.error(f"Ошибка при получении сводки НКО для пользователя {ngo.user_id}: {e}")
        raise

# FIXME: Этот колбэк используется
@ngo_info_router.callback_query(F.data == VIEW_NGO_INFO_CALLBACK_DATA)
async def ngo_info_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик информации о НКО - проверяет наличие данных и показывает меню."""
    await callback.answer()

    ngo_service: NGOService = dispatcher["ngo_service"]
    user_id = callback.from_user.id

    # Проверяем наличие данных НКО
    has_ngo_data = ngo_service.ngo_exists(user_id)

    menu_text = "📋 Информация о НКО\n\n"
    if has_ngo_data:
        ngo_data = ngo_service.get_ngo_data_by_user_id(user_id)
        if ngo_data:
            ngo_name = ngo_data.name
            menu_text += f"🏢 Ваша НКО: {ngo_name}\n\n"

        kb = NGO_INFO_MENU_KEYBOARD
    else:
        menu_text += ("❌ У вас нет сохраненной информации об НКО, "
                      "но вы можете ее указать.\n\n")
        kb = NGO_INFO_MENU_KEYBOARD_NO_NGO

    menu_text += "Выберите действие:"

    await callback.message.answer(
        menu_text,
        reply_markup=kb,
        parse_mode=ParseMode.MARKDOWN,
    )



@ngo_info_router.callback_query(F.data == "view_ngo")
async def view_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик просмотра НКО."""
    await callback.answer()

    ngo_service: NGOService = dispatcher["ngo_service"]
    user_id: int = callback.from_user.id

    # FIXME: перепиши метод на человекочитаемых
    is_exists = ngo_service.ngo_exists(user_id)

    if is_exists:
        ngo = ngo_service.get_ngo_data_by_user_id(user_id)

        summary = get_ngo_summary(ngo)

        await callback.message.answer(
            summary + "\n\nВыберите действие:",
            reply_markup=NGO_BACK_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )

    else:
        await callback.message.answer(
            "❌ У вас пока нет сохраненной информации об НКО.\n\n"
            "Хотите заполнить ее сейчас?",
            reply_markup=NGO_INFO_MENU_KEYBOARD_NO_NGO
        )
        return


NGO_CANCEL_CALLBACK = "ngo_cancel"
NGO_SKIP_CALLBACK = "ngo_skip"

NGO_NAVIGATION_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=NGO_CANCEL_CALLBACK)],
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data=NGO_SKIP_CALLBACK)],
        [InlineKeyboardButton(text="✅ Готово", callback_data=NGO_DONE_CALLBACK)]
    ]
)

NGO_CANCEL_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=NGO_CANCEL_CALLBACK)],
    ]
)

# FIXME: этот колбэк используется
@ngo_info_router.callback_query(F.data == FILL_NGO_INFO_CALLBACK_DATA)
async def fill_ngo_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик заполнения НКО."""
    await callback.answer()

    await callback.message.answer(
        "🏢 Отлично! Давайте заполним информацию о вашей НКО.\n\n"
        "Это поможет мне создавать персонализированный контент с упоминанием вашей организации.\n\n"
        "Укажите наименование НКО:",
        # FIXME: переделай клавиатуру
        reply_markup=NGO_NAVIGATION_KEYBOARD,
    )
    await state.set_state(NGOInfo.waiting_for_ngo_name)


# FIXME: Этот колбэк используется
@ngo_info_router.callback_query(F.data == NGO_DONE_CALLBACK)
async def ngo_done_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик завершения и подтверждения данных НКО."""
    await callback.answer()
    from bot.handlers.start import start_handler

    current_state = await state.get_state()

    if current_state == NGOInfo.waiting_for_ngo_confirmation:
        # Подтверждение данных НКО
        data = await state.get_data()
        ngo = data["ngo_info"]

        # Получаем сервис НКО и сохраняем данные в БД
        ngo_service: NGOService = dispatcher["ngo_service"]


        # Валидируем данные
        is_valid, validation_messages = ngo_service.validate_ngo_data(ngo)

        if not is_valid:
            # TODO: выводи что-нибудь осмысленное
            await callback.message.answer(
                f"❌ Ошибка валидации: {'\n- '.join(validation_messages)}\n\n"
                "Попробуйте снова.",
                reply_markup=NGO_NAVIGATION_KEYBOARD,
            )
            return

        # Сохраняем в БД
        ngo_service.create_ngo(ngo)
        from bot.handlers.start import BACK_TO_START_KEYBOARD

        await callback.message.answer(
            f"✅ Информация о НКО \"{ngo.name}\" успешно сохранена в базу данных!\n\n"
            "Теперь вы можете создавать персонализированный контент.\n\n"
            "💡 Выберите следующее действие или вернитесь в главное меню:",
            reply_markup=BACK_TO_START_KEYBOARD,
        )
        await state.clear()

    else:
        # Просто завершение текущего процесса
        await state.clear()
        await start_handler(callback.message, state)



@ngo_info_router.callback_query(F.data == NGO_CANCEL_CALLBACK)
async def ngo_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены процесса НКО."""
    await callback.answer()
    await state.clear()

    from bot.handlers.start import start_handler

    await callback.message.answer(
        "❎ Процесс сбора информации об НКО отменен.",
    )

    await start_handler(callback.message, state)


@ngo_info_router.callback_query(F.data == NGO_SKIP_CALLBACK)
async def ngo_skip_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска шага в процессе НКО."""
    await callback.answer()

    current_state = await state.get_state()

    if current_state == NGOInfo.waiting_for_ngo_description:
        await state.update_data(ngo_description="Не указано")
        await callback.message.answer(
            f"✅ Описание: Не указано\n\n"
            "🎯 Какие формы деятельности ведет ваша НКО? (например: благотворительность, просвещение, помощь животным и т.д.)\n\n"
            "Можете перечислить через запятую или нажать ⏩ Пропустить.",
            reply_markup=NGO_NAVIGATION_KEYBOARD,
        )
        await state.set_state(NGOInfo.waiting_for_ngo_activities)

    elif current_state == NGOInfo.waiting_for_ngo_activities:
        await state.update_data(ngo_activities="Не указано")
        await callback.message.answer(
            f"✅ Формы деятельности: Не указано\n\n"
            "📞 Укажите контактную информацию для связи (телефон, email, сайт или социальные сети)\n\n"
            "Можете указать любые удобные способы связи или нажать ⏩ Пропустить.",
            reply_markup=NGO_NAVIGATION_KEYBOARD,
        )
        await state.set_state(NGOInfo.waiting_for_ngo_contact)

    elif current_state == NGOInfo.waiting_for_ngo_contact:
        await state.update_data(ngo_contact="Не указано")
        # Показываем итоговую информацию для подтверждения
        data = await state.get_data()
        name = data.get("ngo_name", "")
        description = data.get("ngo_description", "Не указано")
        activities = data.get("ngo_activities", "Не указано")
        contact_info = "Не указано"

        ngo_info = Ngo(
            id_=None,
            user_id=callback.from_user.id,
            name=name,
            description=description,
            activities=activities,
            contacts=contact_info
        )
        await state.update_data(ngo_info=ngo_info)

        summary = (
            f"🏢 **Информация о НКО \"{name}\"**\n\n"
            f"📝 **Описание:** {description}\n\n"
            f"🎯 **Деятельность:** {activities}\n\n"
            f"📞 **Контакты:** {contact_info}\n\n"
            "Подтверждаете данные? Их можно будет изменить позже."
        )

        await callback.message.answer(
            summary,
            reply_markup=NGO_NAVIGATION_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )
        await state.set_state(NGOInfo.waiting_for_ngo_confirmation)


