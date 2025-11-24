from aiogram import Router
from .start import start_router
from .wizard_handler import wizard_router
from .content_plan import content_plan_router
from .content_plan_menu import content_plan_menu_router
from .callbacks import callbacks_router
from .fallback import fallback_router

# Создаем основной роутер и включаем в него все остальные роутеры
router = Router()
router.include_router(start_router)
router.include_router(wizard_router)
router.include_router(content_plan_router)
router.include_router(content_plan_menu_router)
router.include_router(callbacks_router)
router.include_router(fallback_router)

__all__ = [
    "router",
    "start_router",
    "wizard_router", 
    "content_plan_router",
    "content_plan_menu_router"
]
