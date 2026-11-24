from aiogram import Router

from app.infrastructure.telegram.routers.recipient.consent import router as consent_router
from app.infrastructure.telegram.routers.recipient.entry import handle_invite_start
from app.infrastructure.telegram.routers.recipient.schedule import router as schedule_router

router = Router(name="recipient")
router.include_router(consent_router)
router.include_router(schedule_router)

__all__ = ["router", "handle_invite_start"]
