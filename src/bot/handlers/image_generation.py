import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.types.input_file import BufferedInputFile
from aiogram.enums.parse_mode import ParseMode

from app import dp
from bot.states import ImageGeneration
from bot.keyboards.reply import (
    get_image_size_keyboard,
    get_cancel_keyboard,
    get_ngo_main_keyboard,
)

image_generation_router = Router(name="image_generation")

logger = logging.getLogger(__name__)


# Размеры изображений
IMAGE_SIZES = {
    "📱 Квадрат (1024x1024)": (1024, 1024),
    "📺 Горизонтальное (1200x630)": (1200, 630),
    "📱 Вертикальное (630x1200)": (630, 1200),
}


@image_generation_router.message(F.text == "🎨 Сгенерировать изображение")
async def start_image_generation_handler(message: Message, state: FSMContext):
    """Обработчик начала генерации изображения."""
    await state.clear()
    await state.set_state(ImageGeneration.waiting_for_prompt)
    
    await message.answer(
        "🎨 Отлично! Я помогу вам сгенерировать изображение.\n\n"
        "📝 Опишите, какое изображение вы хотите получить.\n"
        "Например: 'Красивый закат над морем, стиль живописи, яркие цвета'\n\n"
        "Или отправьте /cancel для отмены.",
        reply_markup=get_cancel_keyboard(),
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
        reply_markup=get_image_size_keyboard(),
    )


@image_generation_router.message(Command("cancel"))
@image_generation_router.message(F.text == "❌ Отмена")
async def cancel_image_generation_handler(message: Message, state: FSMContext):
    """Обработчик отмены генерации изображения."""
    current_state = await state.get_state()
    if current_state in [ImageGeneration.waiting_for_prompt, ImageGeneration.waiting_for_size]:
        await state.clear()
        await message.answer(
            "❎ Генерация изображения отменена.\n\n"
            "Что вы хотите сделать?",
            reply_markup=get_ngo_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )


@image_generation_router.message(ImageGeneration.waiting_for_size, F.text)
async def size_handler(message: Message, state: FSMContext):
    """Обработчик выбора размера изображения."""
    size_option = message.text
    size = IMAGE_SIZES.get(size_option)
    
    if not size:
        await message.answer(
            "⚠️ Пожалуйста, выберите размер из предложенных вариантов.",
            reply_markup=get_image_size_keyboard(),
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
    
    try:
        # Получаем сервис генерации изображений
        image_service = dp.get("image_generation_service")
        
        if not image_service:
            logger.error("Сервис генерации изображений не найден в dispatcher")
            await message.answer(
                "❌ Ошибка: сервис генерации изображений не настроен.\n"
                "Обратитесь к администратору.",
                reply_markup=get_ngo_main_keyboard(),
            )
            await state.clear()
            return
        
        # Генерируем изображение
        image_bytes = await image_service.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            images=1,
        )
        
        # Отправляем изображение пользователю
        await message.answer_photo(
            photo=BufferedInputFile(image_bytes, "generated_image.png"),
            caption=f"✅ Изображение готово!\n\n📝 Описание: {prompt}",
        )
        
        await message.answer(
            "✨ Изображение успешно сгенерировано!\n\n"
            "Что вы хотите сделать дальше?",
            reply_markup=get_ngo_main_keyboard(),
        )
        
        await state.clear()
        
    except Exception as error:
        logger.exception("Ошибка при генерации изображения: %s", error)
        await message.answer(
            "❌ К сожалению, не удалось сгенерировать изображение.\n"
            f"Ошибка: {str(error)}\n\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=get_ngo_main_keyboard(),
        )
        await state.clear()
