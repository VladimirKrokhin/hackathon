from pathlib import Path

from aiogram import Router
from aiogram.types import FSInputFile

from .image_generation import image_generation_router
from .ngo_info import ngo_info_router
from .start import start_router
from .wizard_handler import create_content_wizard
from .new_generation import  new_generation_router
from .content_plan_generation import content_plan_router
from .content_plan_menu import content_plan_menu_router
from .fallback import fallback_router

# Создаем основной роутер и включаем в него все остальные роутеры
router = Router()
router.include_router(start_router)
router.include_router(ngo_info_router)
router.include_router(new_generation_router)
router.include_router(image_generation_router)
router.include_router(create_content_wizard)
router.include_router(content_plan_router)
router.include_router(content_plan_menu_router)
router.include_router(fallback_router)

ASSETS_BASE_DIR_PATH = Path(__file__).resolve().parent.parent / "assets"

ABOUT_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'about.png'
ABOUT_PHOTO = FSInputFile(path=ABOUT_PHOTO_PATH)

TEXT_SETUP_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'setup.png'
TEXT_SETUP_PHOTO = FSInputFile(path=TEXT_SETUP_PHOTO_PATH)

CALENDAR_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'calendar.png'
CALENDAR_PHOTO = FSInputFile(path=CALENDAR_PHOTO_PATH)

LOCATION_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'location.png'
LOCATION_PHOTO = FSInputFile(path=LOCATION_PHOTO_PATH)

INSPECT_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'inspect.png'
INSPECT_PHOTO = FSInputFile(path=INSPECT_PHOTO_PATH)

NARRATIVE_STYLE_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'narrative_style.png'
NARRATIVE_STYLE_PHOTO = FSInputFile(path=NARRATIVE_STYLE_PHOTO_PATH)

PLATFORM_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'platform.png'
PLATFORM_PHOTO = FSInputFile(path=PLATFORM_PHOTO_PATH)

TEXT_GENERATION_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'text_generation.png'
TEXT_GENERATION_PHOTO = FSInputFile(path=TEXT_GENERATION_PHOTO_PATH)

IMAGE_GENERATION_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'image_generation.png'
IMAGE_GENERATION_PHOTO = FSInputFile(path=IMAGE_GENERATION_PHOTO_PATH)

CARD_GENERATION_PHOTO_PATH = ASSETS_BASE_DIR_PATH / 'card_generation.png'
CARD_GENERATION_PHOTO = FSInputFile(path=CARD_GENERATION_PHOTO_PATH)



__all__ = [
    "router",
]
