import logging
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from services.content_plan_service import ContentPlanService
from services.text_generation import TextGenerationService

from bot import dispatcher

from models import ContentPlan, ContentPlanItem

from bot.states import ContentPlan as ContentPlanState

from bot.handlers.content_plan_generation import PUBLICATION_TIME_INTERVAL_KEYBOARD

from dtos import PromptContext

logger = logging.getLogger(__name__)
content_plan_menu_router = Router(name="content_plan_menu")

VIEW_USER_CONTENT_PLANS_CALLBACK_DATA = "content_plan_view"
CONTENT_PLAN_MENU_CALLBACK_DATA = "content_plan"
CREATE_NEW_CONTENT_PLAN_CALLBACK_DATA = "content_plan_create"

CONTENT_PLAN_MENU_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Посмотреть мои планы", callback_data=VIEW_USER_CONTENT_PLANS_CALLBACK_DATA)],
        [InlineKeyboardButton(text="➕ Создать новый план", callback_data=CREATE_NEW_CONTENT_PLAN_CALLBACK_DATA)],
        [InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="content_plan_back")],
    ]
)


CONTENT_PLAN_LIST_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        # Кнопка создания нового плана
        [InlineKeyboardButton(text="➕ Создать новый план", callback_data=CREATE_NEW_CONTENT_PLAN_CALLBACK_DATA)],
        # Кнопка возврата
        [InlineKeyboardButton(text="⬅️ Назад в меню контент-планов", callback_data=CONTENT_PLAN_MENU_CALLBACK_DATA)],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="content_plan_back")],
    ]
)



# FIXME: Этот обработчик используется
@content_plan_menu_router.callback_query(F.data == CONTENT_PLAN_MENU_CALLBACK_DATA)
async def content_plan_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Показать меню управления контент-планами."""
    await callback.answer()
    await state.clear()
    
    # Получаем количество планов пользователя
    content_plan_service: ContentPlanService = dispatcher["content_plan_service"]
    user_id = callback.from_user.id
    
    plans: tuple[ContentPlan, ...] = await content_plan_service.get_user_plans(user_id)
    plans_count = len(plans)

    text = (
        f"📅 *Управление контент-планами*\n\n"
        f"📊 У вас создано планов: {plans_count}\n\n"
        f"Выберите действие:"
    )

    await callback.message.answer(
        text=text,
        reply_markup=CONTENT_PLAN_MENU_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN
    )



        
# FIXME: этот колбэк используется
@content_plan_menu_router.callback_query(F.data == CREATE_NEW_CONTENT_PLAN_CALLBACK_DATA)
async def create_content_plan_handler(callback: CallbackQuery, state: FSMContext):
    """Начать создание нового контент-плана."""
    await callback.answer()
    
    await callback.message.answer(
        "📅 Давайте создадим контент-план для ваших постов!\n\n"
        "На какой период вы хотите подготовить план?",
        reply_markup=PUBLICATION_TIME_INTERVAL_KEYBOARD,
    )
    await state.set_state(ContentPlanState.waiting_for_period)

# FIXME: Этот колбэк используется
@content_plan_menu_router.callback_query(F.data == VIEW_USER_CONTENT_PLANS_CALLBACK_DATA)
async def view_content_plans_handler(callback: CallbackQuery, state: FSMContext):
    """Показать список существующих планов пользователя."""
    await callback.answer()
    
    content_plan_service: ContentPlanService = dispatcher["content_plan_service"]
    user_id: int = callback.from_user.id
    
    plans = await content_plan_service.get_user_plans(user_id)

    text = "📋 *Ваши контент-планы*\n\n"

    if not plans:
        text += (
            "У вас пока нет созданных контент-планов.\n"
            "Создайте первый план, нажав кнопку ниже:"
        )

        await callback.message.answer(
            text=text,
            # FIXME: Поменяй на другую клавиатуру, где можно только вернуться назад
            reply_markup=CONTENT_PLAN_MENU_KEYBOARD,
            parse_mode=ParseMode.MARKDOWN,
        )

    else:
        # FIXME: Добавь пагинацию


        for i, plan in enumerate(plans, 1):
            text += (
                f"{i}. *{plan.plan_name}*\n"
                f"   📅 Период: {plan.period}\n"
                f"   🆔 ID: `{plan.id_}`\n\n"
            )

        text += "Выберите план для управления:"

        list_keyboard = CONTENT_PLAN_LIST_KEYBOARD.model_copy(deep=True)

        # FIXME: коллбэки не обрабатываются
        for plan in plans:
            button_text = f"{plan.plan_name}"
            callback_data = f"content_plan_manage_{plan.id_}"
            list_keyboard.inline_keyboard.insert(
                0,
                [InlineKeyboardButton(text=button_text, callback_data=callback_data)],
            )


        await callback.message.answer(
            text=text,
            reply_markup=list_keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        

# === НАВИГАЦИЯ ===
@content_plan_menu_router.callback_query(F.data == "content_plan_back")
async def back_to_start_menu_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""

    from bot.handlers.start import start_handler

    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


@content_plan_menu_router.callback_query(F.data == "skip_step")
async def skip_step_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска шага."""
    await callback.answer()
    await callback.message.answer(
        "Шаг пропущен.",
        reply_markup=ReplyKeyboardRemove(),
    )


@content_plan_menu_router.callback_query(F.data == "done")
async def done_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик завершения процесса."""
    from bot.handlers.start import start_handler

    await callback.answer()
    await state.clear()
    await start_handler(callback.message, state)


# === ОБРАБОТЧИКИ УПРАВЛЕНИЯ ПЛАНОМ ===

@content_plan_menu_router.callback_query(F.data.startswith("content_plan_manage_"))
async def manage_specific_plan_handler(callback: CallbackQuery, state: FSMContext):
    """
    Меню управления конкретным контент-планом.
    Показывает список постов (элементов плана).
    """
    await callback.answer()

    # Извлекаем ID плана из callback_data
    plan_id = int(callback.data.split("_")[-1])

    content_plan_service: ContentPlanService = dispatcher["content_plan_service"]
    plan = await content_plan_service.get_plan_by_id(plan_id)

    if not plan:
        await callback.message.answer("❌ Не удалось найти указанный план.")
        return

    text = (
        f"📂 *План:* {plan.plan_name}\n"
        f"📅 *Период:* {plan.period}\n\n"
        f"Выберите тему поста для работы:"
    )

    # Создаем клавиатуру со списком тем
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Сортируем по дате, если возможно
    sorted_items = sorted(plan.items, key=lambda x: x.publication_date) if plan.items else []

    for item in sorted_items:
        # Форматируем дату: 25.10
        date_str = item.publication_date.strftime("%d.%m")
        # Обрезаем заголовок, чтобы влез в кнопку
        btn_text = f"{date_str} | {item.content_title[:20]}..."

        # callback для выбора конкретного поста
        callback_data = f"cp_item_view_{item.id_}"

        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=btn_text, callback_data=callback_data)]
        )

    # Кнопка назад к списку планов
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="⬅️ Назад к списку планов", callback_data=VIEW_USER_CONTENT_PLANS_CALLBACK_DATA)]
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@content_plan_menu_router.callback_query(F.data.startswith("cp_item_view_"))
async def view_plan_item_handler(callback: CallbackQuery, state: FSMContext):
    """
    Просмотр деталей конкретного поста из плана и кнопка генерации.
    """
    await callback.answer()

    item_id = int(callback.data.split("_")[-1])
    content_plan_service: ContentPlanService = dispatcher["content_plan_service"]

    # Получаем элемент плана
    item: ContentPlanItem = await content_plan_service.get_plan_item_by_id(item_id)

    if not item:
        await callback.message.answer("❌ Элемент плана не найден.")
        return

    # Формируем текст карточки поста
    date_str = item.publication_date.strftime("%d.%m.%Y")
    status_icon = "✅" if item.status == "published" else "⏳"

    text = (
        f"📝 *Детали публикации*\n\n"
        f"📌 *Тема:* {item.content_title}\n"
        f"📅 *Дата:* {date_str}\n"
        f"📊 *Статус:* {item.status} {status_icon}\n\n"
        f"📄 *Описание/Идея:*\n_{item.content_text}_"
    )
    await state.update_data(context=text)
    # Клавиатура действий
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Сгенерировать текст поста", callback_data=f"cp_item_gen_{item.id_}")],
        # Кнопка "Назад" должна возвращать в меню самого плана.
        # Нам нужен plan_id, он есть в item.content_plan_id
        [InlineKeyboardButton(text="⬅️ Назад к плану", callback_data=f"content_plan_manage_{item.content_plan_id}")]
    ])

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


async def get_text_edit_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Отредактировать текст", callback_data="content_plan_edit_text")],
            [InlineKeyboardButton(text="⬅️ К деталям темы", callback_data=f"cp_item_view_{item_id}")],
        ]
    )


# === РЕДАКТИРОВАНИЕ СГЕНЕРИРОВАННОГО ПОСТА ===
@content_plan_menu_router.callback_query(F.data.startswith("cp_item_gen_"))
async def generate_post_from_plan_handler(callback: CallbackQuery, state: FSMContext):
    """
    Запуск генерации текста поста на основе элемента контент-плана.
    """
    item_id = int(callback.data.split("_")[-1])
    content_plan_service: ContentPlanService = dispatcher["content_plan_service"]
    text_gen_service: TextGenerationService = dispatcher["text_content_generation_service"]

    item: ContentPlanItem = await content_plan_service.get_plan_item_by_id(item_id)

    if not item:
        await callback.message.answer("❌ Ошибка: элемент плана не найден.")
        return

    loading_msg = await callback.message.answer("🤖 *Генерирую текст...* Это может занять около 30 секунд.")

    try:
        # Здесь использую описание из плана как цель. По хорошему нужно сделать отдельный dto

        user_prompt = (
            f"Напиши пост для социальных сетей на тему: '{item.content_title}'. "
            f"Дополнительные детали и контекст: {item.content_text}. "
            f"Пост должен быть вовлекающим и соответствовать НКО."
        )

        # Создаем контекст.
        context = PromptContext(
            goal=item.content_text,  # Используем описание как цель
        )

        # Вызываем сервис генерации
        generated_text = await text_gen_service.generate_text(
            context=context,
            user_prompt=user_prompt
        )
        await state.update_data(generated_text=generated_text)

        # Отправляем результат
        await loading_msg.delete()

        await callback.message.answer(
            "✅ *Сгенерированный пост:*\n\n",
            parse_mode=ParseMode.MARKDOWN
        )
        await state.update_data(item_id=item.id_)

        keyboard = await get_text_edit_keyboard(item.id_)

        await callback.message.answer(
            text=generated_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Ошибка генерации поста: {e}")
        await callback.message.answer("❌ Произошла ошибка при генерации текста. Попробуйте позже.")


@content_plan_menu_router.callback_query(F.data == "content_plan_edit_text")
async def text_edit_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    await callback.message.answer(
        "✏️ **Редактирование текста**\n\n"
        "Опишите, как именно нужно изменить текст:\n\n"
        "_Например: «Сделай короче», «Измени стиль», «Добавь призыв к действию»_",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode=ParseMode.MARKDOWN,
    )
    await state.set_state(ContentPlanState.waiting_for_text_edit)


@content_plan_menu_router.message(ContentPlanState.waiting_for_text_edit, F.text)
async def text_edit_handler(message: Message, state: FSMContext):
    edit_instruction = message.text.strip()
    await state.update_data(edit_instruction=edit_instruction)

    await message.answer(
        "✏️ **Редактируем текст...**",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        # Получаем текущий сгенерированный текст
        data = await state.get_data()
        context = PromptContext.from_dict({"goal": data.get("context", "")})
        current_text = data.get("generated_text", "")

        text_gen_service: TextGenerationService = dispatcher["text_content_generation_service"]
        edited_text = await text_gen_service.refactor_text(
            context=context,
            post_to_edit=current_text,
            user_prompt=edit_instruction
        )

        await state.update_data(generated_text=edited_text)

        item_id = await state.get_value("item_id")
        keyboard = await get_text_edit_keyboard(item_id)

        await message.answer(
            "✅ **Текст отредактирован!**\n\n"
            f"{edited_text}\n\n"
            "**Что делать с текстом?**",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )

    except Exception as e:
        logger.exception(f"Ошибка редактирования текста: {e}")
        item_id = await state.get_value("item_id")
        keyboard = await get_text_edit_keyboard(item_id)
        await message.answer(
            "❌ Ошибка редактирования текста. Попробуйте снова.",
            reply_markup=keyboard,
        )











