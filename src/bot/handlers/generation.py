import io
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.enums.parse_mode import ParseMode
from aiogram.types.input_file import BufferedInputFile

from app import dp
from bot.states import ContentGeneration
from bot.keyboards.inline import get_post_generation_keyboard
from bot.utils import (
    get_caption_for_card_type,
    get_color_by_goal,
    get_secondary_color_by_goal,
    get_template_by_platform,
    get_title_by_goal,
)
from services.content_generation import TextContentGenerationService
from services.card_generation import CardGenerationService

generation_router = Router(name="generation")

logger = logging.getLogger(__name__)


async def complete_generation_handler(message: Message, state: FSMContext):
    """Универсальная функция завершения генерации контента."""
    data = await state.get_data()
    user_text = data.get("user_text", "")
    
    # Определяем цель на основе данных
    goal = data.get("goal", "🎯 Рассказать о мероприятии")
    platform = data.get("platform", "📱 ВКонтакте (для молодежи)")
    
    # Получаем информацию об НКО из базы данных
    ngo_service = dp["ngo_service"]
    user_id = message.from_user.id
    ngo_data = ngo_service.get_ngo_data(user_id)
    
    # Обновляем данные пользователя информацией из БД
    if ngo_data:
        data.update(ngo_data)
    
    # Устанавливаем значения по умолчанию
    ngo_name = ngo_data.get("ngo_name", "Ваша НКО") if ngo_data else "Ваша НКО"
    ngo_contact = ngo_data.get("ngo_contact", "тел: +7 (XXX) XXX-XX-XX") if ngo_data else "тел: +7 (XXX) XXX-XX-XX"
    
    generated_post = None

    await message.answer(
        "🧠 Генерирую контент...",
        reply_markup=ReplyKeyboardRemove(),
        )

    try:
        text_generation_service: TextContentGenerationService = dp["text_content_generation_service"]
        generated_post = await text_generation_service.generate_text_content(data, user_text)
        await state.update_data(generated_post=generated_post)
    except Exception as error:
        logger.exception("Ошибка при генерации текста: %s", error)
        await message.answer(
            "⚠️ Не удалось получить ответ.",
            reply_markup=ReplyKeyboardRemove(),
        )
        raise error

    # Показываем сгенерированный пост
    await message.answer(
        f"✅ Ваш сгенерированный контент:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        generated_post,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
        )

    # Обработка изображения для карточки
    image_source = data.get("image_source")
    user_image = data.get("user_image")
    image_prompt = data.get("image_prompt")
    generated_image = None

    logger.info(f"Обработка изображения: source={image_source}, user_image={'есть' if user_image else 'нет'}, prompt={image_prompt[:50] + '...' if image_prompt and len(image_prompt) > 50 else image_prompt}")

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
        # Автоматически переходим к генерации карточек с существующим изображением
        logger.info("Пользователь выбрал AI изображение для контента - пропускаем выбор фото для карточки")
        await generate_cards_handler(message, state)
        return

    # Спрашиваем у пользователя выбор фото для карточки только если не выбрана генерация ИИ для контента
    await message.answer(
        "🖼️ **Выберите источник фото для информационных карточек:**",
        reply_markup=ReplyKeyboardRemove(),
    )

    from bot.keyboards.inline import get_card_photo_choice_keyboard
    await message.answer(
        "Какое фото использовать для карточки?",
        reply_markup=get_card_photo_choice_keyboard(),
    )
    await state.set_state(ContentGeneration.waiting_for_card_photo_choice)
    return


async def generate_cards_handler(message: Message, state: FSMContext):
    """Функция для генерации карточек после выбора фото."""
    data = await state.get_data()
    user_text = data.get("user_text", "")

    # Определяем цель на основе данных
    goal = data.get("goal", "🎯 Рассказать о мероприятии")
    platform = data.get("platform", "📱 ВКонтакте (для молодежи)")

    # Получаем информацию об НКО из базы данных
    ngo_service = dp["ngo_service"]
    user_id = message.from_user.id
    ngo_data = ngo_service.get_ngo_data(user_id)

    # Устанавливаем значения по умолчанию
    ngo_name = ngo_data.get("ngo_name", "Ваша НКО") if ngo_data else "Ваша НКО"
    ngo_contact = ngo_data.get("ngo_contact", "тел: +7 (XXX) XXX-XX-XX") if ngo_data else "тел: +7 (XXX) XXX-XX-XX"

    generated_post = data.get("generated_post", "")
    # Получаем общее изображение из состояния (для показа отдельно после генерации карточек)
    image_source = data.get("image_source", "")
    generated_image = None
    if image_source == "🤖 Сгенерировать ИИ":
        generated_image = data.get("ai_generated_image")
    elif image_source == "📎 Загрузить своё":
        generated_image = data.get("user_image")

    await message.answer(
        "🎨 Создаю информационные карточки...",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        # Получаем параметры карточек из состояния
        card_image_source = data.get("card_image_source")
        card_generated_image = None

        logger.info(f"Генерация карточек с image_source='{card_image_source}'")

        # Обработка выбранного пользователем фото для карточки
        if card_image_source == "🤖 AI сгенерирует фото":
            card_image_prompt = data.get("card_image_prompt")
            if not card_image_prompt:
                await message.answer(
                    "❌ Не указан промпт для генерации фото. Используем карточки без фото.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                card_generated_image = None
            else:
                await message.answer(
                    "🤖 Генерирую фото для карточки ИИ...",
                    reply_markup=ReplyKeyboardRemove(),
                )
                try:
                    image_generation_service = dp.get("image_generation_service")
                    if not image_generation_service:
                        raise Exception("Сервис генерации изображений не инициализирован")

                    smart_card_prompt = card_image_prompt
                    if data.get("generation_mode") == "structured":
                        event_context = f". Для события '{data.get('event_type', '')}' в '{data.get('event_place', '')}'"
                        smart_card_prompt += event_context

                    logger.info(f"Генерируем фото для карточки с промпт: {smart_card_prompt}")
                    card_generated_image = await image_generation_service.generate_image(
                        prompt=smart_card_prompt,
                        width=1024,
                        height=768
                    )
                    await message.answer(
                        "✅ Фото для карточки готово!",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                except Exception as e:
                    logger.exception(f"Ошибка генерации фото для карточки: {e}")
                    await message.answer(
                        "⚠️ Не удалось сгенерировать фото для карточки. Используем без фото.",
                        reply_markup=ReplyKeyboardRemove(),
                    )
                    card_generated_image = None

        elif card_image_source == "📎 Загрузить своё фото":
            card_user_image = data.get("card_user_image")
            if card_user_image:
                card_generated_image = card_user_image
                await message.answer(
                    "✅ Использую ваше фото для карточки.",
                    reply_markup=ReplyKeyboardRemove(),
                )
            else:
                await message.answer(
                    "❌ Фото не загружено. Используем карточки без фото.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                card_generated_image = None

        elif card_image_source == "🚫 Без фото":
            card_generated_image = None
            await message.answer(
                "✅ Выбрано: Без фото для карточки",
                reply_markup=ReplyKeyboardRemove(),
            )
        # Логируем ключевые данные для отладки
        logger.info(f"Данные для карточки: goal='{goal}', platform='{platform}', ngo_name='{ngo_name}', ngo_contact='{ngo_contact}'")
        logger.info(f"Сгенерированный пост: {generated_post[:100]}...")

        # Определяем подзаголовок в зависимости от режима
        if data.get("generation_mode") == "structured":
            subtitle = f"Событие: {data.get('event_type', 'мероприятие')}"
        else:
            subtitle = f"Для {data.get('event_audience', 'наших подопечных')}"

        # Обеспечиваем, что все ключевые значения не пустые
        safe_content = generated_post if generated_post and isinstance(generated_post, str) else "Сгенерированный контент"
        safe_content = f"{safe_content[:250]}..." if len(safe_content) > 250 else safe_content

        template_data = {
            "title": get_title_by_goal(goal or "🎯 Рассказать о мероприятии") or "Основная информация",
            "subtitle": subtitle or "",
            "content": safe_content,
            "org_name": ngo_name or "Ваша НКО",
            "contact_info": ngo_contact or "",
            "primary_color": get_color_by_goal(goal or "🎯 Рассказать о мероприятии") or "#667eea",
            "secondary_color": get_secondary_color_by_goal(goal or "🎯 Рассказать о мероприятии") or "#764ba2",
            "text_color": "#333333",
            "background_color": "#f5f7fa",
        }

        logger.info(f"Template data keys: {list(template_data.keys())}")
        logger.info(f"Title: '{template_data['title']}', Content length: {len(template_data['content'])}")
        logger.info(f"Org name: '{template_data['org_name']}', Contact: '{template_data['contact_info']}'")
        logger.warning(f"Goal: '{goal}', Platform: '{platform}' (debugging card issue)")

        # Добавляем специфические данные для структурированной формы
        if data.get("generation_mode") == "structured":
            template_data.update({
                "event_type": data.get('event_type', ''),
                "event_date": data.get('event_date', ''),
                "event_place": data.get('event_place', ''),
                "event_audience": data.get('event_audience', ''),
                "event_details": data.get('event_details', ''),
                "narrative_style": data.get('narrative_style', ''),
            })

        # Добавляем данные для свободной формы
        if data.get("generation_mode") == "free_form" or not data.get("generation_mode"):
            template_data.update({
                "user_description": data.get('user_text', ''),
                "narrative_style": data.get('narrative_style', ''),
            })

        # Добавляем изображение в данные шаблона если есть (карточка имеет приоритет над общим изображением)
        card_image_to_use = card_generated_image if card_generated_image else generated_image
        if card_image_to_use:
            import base64
            image_base64 = base64.b64encode(card_image_to_use).decode('utf-8')
            template_data["background_image"] = f"data:image/png;base64,{image_base64}"
            logger.info(f"Background image added to template data: {len(image_base64)} chars")
        else:
            logger.info("No background image added to template data")

        # Логируем полные данные шаблона для отладки
        logger.info(f"Full template_data: {template_data}")

        template_name = get_template_by_platform(platform)
        logger.info(f"Using template: {template_name} for platform: {platform}")
        card_generation_service: CardGenerationService = dp["card_generation_service"]

        cards = await card_generation_service.generate_multiple_cards(
            template_name=template_name,
            data=template_data,
            platform=platform,
        )

        if not cards:
            raise ValueError("Генератор карточек ничего не вернул")

        # Отправляем сгенерированное ИИ изображение сначала отдельно
        if generated_image and image_source == "🤖 Сгенерировать ИИ":
            await message.answer(
                "🖼️ **Вот ваше сгенерированное изображение:**",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode=ParseMode.MARKDOWN,
            )
            await message.answer_photo(
                photo=BufferedInputFile(generated_image, "ai_generated_image.png"),
                caption="🎨 Сгенерированное ИИ изображение",
                reply_markup=ReplyKeyboardRemove(),
            )

        await message.answer(
            "🎨 Вот ваши карточки для соцсетей:",
            reply_markup=ReplyKeyboardRemove(),
            )

        for card_type, image_bytes in cards.items():
            caption = get_caption_for_card_type(card_type, platform)
            image_stream = image_bytes
            await message.answer_photo(
                photo=BufferedInputFile(image_stream, f"{card_type}.png"),
                caption=caption,
                reply_markup=ReplyKeyboardRemove(),
            )

        await message.answer(
            "✨ Все материалы готовы к публикации! Что хотите сделать дальше?",
            reply_markup=get_post_generation_keyboard(),
        )
        await state.set_state(ContentGeneration.waiting_for_confirmation)

    except Exception as error:
        logger.exception("Ошибка при генерации карточек: %s", error)
        await message.answer(
            "❌ Не удалось сформировать карточки.",
            reply_markup=ReplyKeyboardRemove(),
        )
        raise error


# @generation_router.message(ContentGeneration.waiting_for_user_text, F.text)
# async def user_text_handler(message: Message, state: FSMContext):
#     """Обработчик для старого режима генерации (совместимость)."""
#     user_text = message.text.strip()
#     await state.update_data(user_text=user_text)
#     await complete_generation_handler(message, state)
