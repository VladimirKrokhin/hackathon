import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.states import ContentGeneration
from src.bot.keyboards.reply import (
    GOAL_OPTIONS,
    AUDIENCE_OPTIONS,
    PLATFORM_OPTIONS,
    FORMAT_OPTIONS,
    VOLUME_OPTIONS,
    YES_NO_OPTIONS,
    DONE_OPTION,
    SKIP_OPTION,
    get_goal_keyboard,
    get_audience_keyboard,
    get_platform_keyboard,
    get_format_keyboard,
    get_volume_keyboard,
    get_yes_no_keyboard,
    get_skip_keyboard,
    get_example_keyboard,
)

questionnaire_router = Router(name="questionnaire")
logger = logging.getLogger(__name__)


@questionnaire_router.message(ContentGeneration.waiting_for_goal, F.text)
async def goal_handler(message: Message, state: FSMContext):
    goal = message.text.strip()
    if goal not in GOAL_OPTIONS:
        await message.answer(
            "Пожалуйста, выберите цель из предложенных вариантов.",
            reply_markup=get_goal_keyboard(),
        )
        return

    await state.update_data(goal=goal)
    await message.answer(
        "👥 Кто ваша целевая аудитория? (можно выбрать несколько вариантов, нажмите ✅ Готово когда закончите)",
        reply_markup=get_audience_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_audience)


@questionnaire_router.message(ContentGeneration.waiting_for_audience, F.text)
async def audience_handler(message: Message, state: FSMContext):
    selection = message.text.strip()
    data = await state.get_data()
    audience_list = data.get("audience", [])

    if selection == DONE_OPTION:
        if not audience_list:
            await message.answer("Пожалуйста, выберите хотя бы одну аудиторию.")
            return

        await message.answer(
            "📱 На какой платформе будет публиковаться контент?",
            reply_markup=get_platform_keyboard(),
        )
        await state.set_state(ContentGeneration.waiting_for_platform)
        return

    if selection not in AUDIENCE_OPTIONS:
        await message.answer(
            "Используйте кнопки ниже, чтобы выбрать подходящую аудиторию. "
            "Когда закончите — нажмите ✅ Готово.",
            reply_markup=get_audience_keyboard(audience_list),
        )
        return

    if selection in audience_list:
        audience_list.remove(selection)
    else:
        audience_list.append(selection)

    await state.update_data(audience=audience_list)
    selected = "\n".join(f"• {item}" for item in audience_list) or "Пока ничего не выбрано"
    await message.answer(
        f"Текущий выбор аудитории:\n{selected}\n\n"
        "Выберите ещё или нажмите ✅ Готово",
        reply_markup=get_audience_keyboard(audience_list),
    )


@questionnaire_router.message(ContentGeneration.waiting_for_platform, F.text)
async def platform_handler(message: Message, state: FSMContext):
    platform = message.text.strip()
    if platform not in PLATFORM_OPTIONS:
        await message.answer(
            "Пожалуйста, выберите платформу из списка.",
            reply_markup=get_platform_keyboard(),
        )
        return

    await state.update_data(platform=platform)
    await message.answer(
        "📊 Какой формат контента вам нужен? (можно выбрать несколько)",
        reply_markup=get_format_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_format)


@questionnaire_router.message(ContentGeneration.waiting_for_format, F.text)
async def format_handler(message: Message, state: FSMContext):
    selection = message.text.strip()
    data = await state.get_data()
    format_list = data.get("format", [])

    if selection == DONE_OPTION:
        if not format_list:
            await message.answer("Пожалуйста, выберите хотя бы один формат контента.")
            return

        await message.answer(
            "🎉 Есть ли у вас конкретное мероприятие для продвижения?",
            reply_markup=get_yes_no_keyboard(),
        )
        await state.set_state(ContentGeneration.waiting_for_has_event)
        return

    if selection not in FORMAT_OPTIONS:
        await message.answer(
            "Используйте кнопки из списка. Когда закончите — нажмите ✅ Готово.",
            reply_markup=get_format_keyboard(format_list),
        )
        return

    if selection in format_list:
        format_list.remove(selection)
    else:
        format_list.append(selection)

    await state.update_data(format=format_list)
    selected = "\n".join(f"• {item}" for item in format_list) or "Пока ничего не выбрано"
    await message.answer(
        f"Текущий выбор форматов:\n{selected}\n\n"
        "Выберите ещё или нажмите ✅ Готово",
        reply_markup=get_format_keyboard(format_list),
    )


@questionnaire_router.message(ContentGeneration.waiting_for_has_event, F.text)
async def has_event_handler(message: Message, state: FSMContext):
    answer = message.text.strip()
    if answer not in YES_NO_OPTIONS:
        await message.answer(
            "Пожалуйста, используйте кнопки «Да» или «Нет».",
            reply_markup=get_yes_no_keyboard(),
        )
        return

    has_event = answer == YES_NO_OPTIONS[0]
    await state.update_data(has_event=has_event)

    if has_event:
        await message.answer(
            "📅 Когда и где состоится мероприятие?",
            reply_markup=get_skip_keyboard(),
        )
        await state.set_state(ContentGeneration.waiting_for_event_details)
        return

    await message.answer(
        "📏 Какой объём контента вам нужен?",
        reply_markup=get_volume_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_volume)


@questionnaire_router.message(ContentGeneration.waiting_for_event_details, F.text)
async def event_details_handler(message: Message, state: FSMContext):
    details = "" if message.text.strip() == SKIP_OPTION else message.text.strip()
    await state.update_data(event_details=details)

    await message.answer(
        "📏 Какой объём контента вам нужен?",
        reply_markup=get_volume_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_volume)


@questionnaire_router.message(ContentGeneration.waiting_for_volume, F.text)
async def volume_handler(message: Message, state: FSMContext):
    volume = message.text.strip()
    if volume not in VOLUME_OPTIONS:
        await message.answer(
            "Пожалуйста, выберите один из предложенных вариантов объёма.",
            reply_markup=get_volume_keyboard(),
        )
        return

    await state.update_data(volume=volume)
    await message.answer(
        "✏️ Теперь расскажите подробнее, о чём вы хотите рассказать в посте. "
        "Это поможет мне создать максимально релевантный контент.",
        reply_markup=get_example_keyboard(
            "Пример: Нужны волонтёры для помощи детям с подготовкой к школе"
        ),
    )
    await state.set_state(ContentGeneration.waiting_for_user_text)