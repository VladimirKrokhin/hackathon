from aiogram import Router

from .start import start_router
from .questionnaire import questionnaire_router
from .generation import generation_router
from .refactoring import refactoring_router
from .content_plan import content_plan_router
from .callbacks import callbacks_router
from .fallback import fallback_router
from .ngo_info import ngo_info_router

router = Router(name="main_router")
router.include_router(start_router)
router.include_router(ngo_info_router)
router.include_router(questionnaire_router)
router.include_router(generation_router)
router.include_router(refactoring_router)
router.include_router(content_plan_router)
router.include_router(callbacks_router)
router.include_router(fallback_router)

__all__ = ["router"]
