"""
Обработчики для работы с данными об НКО через базу данных
"""
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command
from app import dp

from bot.states import NGOInfo, ContentGeneration
from bot.keyboards.reply import (
    get_goal_keyboard,
    get_ngo_main_keyboard,
    get_ngo_navigation_keyboard,
    SKIP_OPTION,
)

ngo_info_router = Router(name="ngo_info")
logger = logging.getLogger(__name__)


@ngo_info_router.message(Command("ngo"))
async def ngo_command_handler(message: Message, state: FSMContext):
    """Обработчик команды /ngo - запуск процесса сбора информации об НКО."""
    # Очищаем состояние для нового процесса
    await state.clear()
    
    # Проверяем наличие данных об НКО в БД
    ngo_service = dp["ngo_service"]
    user_id = message.from_user.id
    
    if ngo_service.ngo_exists(user_id):
        # Если у пользователя уже есть данные НКО, показываем главное меню
        await message.answer(
            "🏢 У вас уже есть информация о НКО! Выберите действие:",
            reply_markup=get_ngo_main_keyboard(),
        )
        await state.set_state(NGOInfo.waiting_for_ngo_name)
        return
    
    # Если данных НКО нет, начинаем сбор
    await message.answer(
        "🏢 Отлично! Давайте заполним информацию о вашей НКО.\n\n"
        "Это поможет мне создавать персонализированный контент с упоминанием вашей организации.",
        reply_markup=get_ngo_navigation_keyboard(),
    )
    await state.set_state(NGOInfo.waiting_for_ngo_name)


@ngo_info_router.message(NGOInfo.waiting_for_ngo_name, F.text)
async def ngo_name_handler(message: Message, state: FSMContext):
    """Обработчик ввода названия НКО."""
    text = message.text.strip()
    
    if text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❎ Процесс сбора информации об НКО отменен.",
            reply_markup=get_ngo_main_keyboard(),
        )
        return
    
    if not text:
        await message.answer(
            "Пожалуйста, введите название вашей НКО.",
            reply_markup=get_ngo_navigation_keyboard(),
        )
        return
    
    await state.update_data(ngo_name=text)
    
    await message.answer(
        f"✅ Название: {text}\n\n"
        "📝 Теперь расскажите, чем занимается ваша НКО? (опишите основную деятельность, цели, задачи)\n\n"
        "Можете ввести подробное описание или нажать ⏩ Пропустить, если не хотите заполнять это поле.",
        reply_markup=get_ngo_navigation_keyboard(),
    )
    await state.set_state(NGOInfo.waiting_for_ngo_description)


@ngo_info_router.message(NGOInfo.waiting_for_ngo_description, F.text)
async def ngo_description_handler(message: Message, state: FSMContext):
    """Обработчик ввода описания НКО."""
    text = message.text.strip()
    
    if text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❎ Процесс сбора информации об НКО отменен.",
            reply_markup=get_ngo_main_keyboard(),
        )
        return
    
    if text == "⏩ Пропустить":
        description = "Не указано"
    else:
        description = text
    
    await state.update_data(ngo_description=description)
    
    await message.answer(
        f"✅ Описание: {description}\n\n"
        "🎯 Какие формы деятельности ведет ваша НКО? (например: благотворительность, просвещение, помощь животным и т.д.)\n\n"
        "Можете перечислить через запятую или нажать ⏩ Пропустить.",
        reply_markup=get_ngo_navigation_keyboard(),
    )
    await state.set_state(NGOInfo.waiting_for_ngo_activities)


@ngo_info_router.message(NGOInfo.waiting_for_ngo_activities, F.text)
async def ngo_activities_handler(message: Message, state: FSMContext):
    """Обработчик ввода форм деятельности НКО."""
    text = message.text.strip()
    
    if text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❎ Процесс сбора информации об НКО отменен.",
            reply_markup=get_ngo_main_keyboard(),
        )
        return
    
    if text == "⏩ Пропустить":
        activities = "Не указано"
    else:
        activities = text
    
    await state.update_data(ngo_activities=activities)
    
    await message.answer(
        f"✅ Формы деятельности: {activities}\n\n"
        "📞 Укажите контактную информацию для связи (телефон, email, сайт или социальные сети)\n\n"
        "Можете указать любые удобные способы связи или нажать ⏩ Пропустить.",
        reply_markup=get_ngo_navigation_keyboard(),
    )
    await state.set_state(NGOInfo.waiting_for_ngo_contact)


@ngo_info_router.message(NGOInfo.waiting_for_ngo_contact, F.text)
async def ngo_contact_handler(message: Message, state: FSMContext):
    """Обработчик ввода контактной информации НКО."""
    text = message.text.strip()
    
    if text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❎ Процесс сбора информации об НКО отменен.",
            reply_markup=get_ngo_main_keyboard(),
        )
        return
    
    if text == "⏩ Пропустить":
        contact = "Не указано"
    else:
        contact = text
    
    await state.update_data(ngo_contact=contact)
    
    # Показываем итоговую информацию для подтверждения
    data = await state.get_data()
    name = data.get("ngo_name", "")
    description = data.get("ngo_description", "Не указано")
    activities = data.get("ngo_activities", "Не указано")
    contact_info = contact
    
    summary = (
        f"🏢 **Информация о НКО \"{name}\"**\n\n"
        f"📝 **Описание:** {description}\n\n"
        f"🎯 **Деятельность:** {activities}\n\n"
        f"📞 **Контакты:** {contact_info}\n\n"
        "Подтверждаете данные? Их можно будет изменить позже."
    )
    
    await message.answer(
        summary,
        reply_markup=get_ngo_navigation_keyboard(),
    )
    await state.set_state(NGOInfo.waiting_for_ngo_confirmation)


@ngo_info_router.message(NGOInfo.waiting_for_ngo_confirmation, F.text)
async def ngo_confirmation_handler(message: Message, state: FSMContext):
    """Обработчик подтверждения данных об НКО."""
    text = message.text.strip()
    
    if text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❎ Процесс сбора информации об НКО отменен.",
            reply_markup=get_ngo_main_keyboard(),
        )
        return
    
    if text == "⏩ Пропустить":
        # Если пользователь пропустил, все равно сохраняем собранные данные
        pass
    
    if text == "✅ Готово":
        data = await state.get_data()
        ngo_name = data.get("ngo_name", "")
        
        # Получаем сервис НКО и сохраняем данные в БД
        ngo_service = dp["ngo_service"]
        user_id = message.from_user.id
        
        ngo_data = {
            "ngo_name": ngo_name,
            "description": data.get("ngo_description", "Не указано"),
            "activities": data.get("ngo_activities", "Не указано"),
            "contact": data.get("ngo_contact", "Не указано"),
        }
        
        # Валидируем данные
        is_valid, validation_message = ngo_service.validate_ngo_data(ngo_data)
        if not is_valid:
            await message.answer(
                f"❌ Ошибка валидации: {validation_message}\n\n"
                "Попробуйте снова.",
                reply_markup=get_ngo_navigation_keyboard(),
            )
            return
        
        # Сохраняем в БД
        success = ngo_service.create_or_update_ngo(user_id, ngo_data)
        
        if success:
            await message.answer(
                f"✅ Информация о НКО \"{ngo_name}\" успешно сохранена в базу данных!\n\n"
                "Теперь вы можете создавать персонализированный контент.\n\n"
                "Какова основная цель вашего поста?",
                reply_markup=get_goal_keyboard(),
            )
            await state.clear()
            await state.set_state(ContentGeneration.waiting_for_goal)
        else:
            await message.answer(
                "❌ Не удалось сохранить данные. Попробуйте позже.",
                reply_markup=get_ngo_navigation_keyboard(),
            )
        return
    
    # Если пользователь ввел другой текст, просим использовать кнопки
    await message.answer(
        "Пожалуйста, используйте кнопки для подтверждения или отмены.",
        reply_markup=get_ngo_navigation_keyboard(),
    )


# Обработчик для просмотра текущей информации об НКО
@ngo_info_router.message(F.text == "📋 Посмотреть мою НКО")
async def view_ngo_info_handler(message: Message, state: FSMContext):
    """Обработчик для просмотра текущей информации об НКО."""
    ngo_service = dp["ngo_service"]
    user_id = message.from_user.id
    
    summary = ngo_service.get_ngo_summary(user_id)
    
    if not summary:
        await message.answer(
            "❌ У вас пока нет сохраненной информации об НКО.\n\n"
            "Хотите заполнить ее сейчас?",
            reply_markup=get_ngo_main_keyboard(),
        )
        return
    
    await message.answer(
        summary + "Выберите действие:",
        reply_markup=get_ngo_main_keyboard(),
    )


# Обработчик для обновления данных НКО
@ngo_info_router.message(F.text == "🔄 Обновить данные НКО")
async def update_ngo_info_handler(message: Message, state: FSMContext):
    """Обработчик для обновления данных НКО."""
    await state.clear()
    await state.set_state(NGOInfo.waiting_for_ngo_name)
    await message.answer(
        "🔄 Обновление данных НКО\n\n"
        "Введите новое название НКО (или текущее, если не хотите менять):",
        reply_markup=get_ngo_navigation_keyboard(),
    )


# Обработчик для создания контента без НКО
@ngo_info_router.message(F.text == "✨ Создать контент без НКО")
async def create_content_without_ngo_handler(message: Message, state: FSMContext):
    """Обработчик для создания контента без информации об НКО."""
    await state.clear()
    await state.update_data(has_ngo_info=False)
    
    await message.answer(
        "✨ Понятно! Создаем контент без упоминания НКО.\n\n"
        "Какова основная цель вашего поста?",
        reply_markup=get_goal_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_goal)
