from aiogram import Router

from .image_generation import image_generation_router
from .ngo_info import ngo_info_router
from .start import start_router
from .wizard_handler import create_content_wizard
from .new_generation import new_generation_router
from .content_plan_generation import content_plan_router
from .content_plan_menu import content_plan_menu_router
from .text_editing import text_editing_router
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
router.include_router(text_editing_router)
router.include_router(fallback_router)

__all__ = [
    "router",
]
