from aiogram import Router

from app.infrastructure.telegram.routers.author.consent import router as consent_router
from app.infrastructure.telegram.routers.author.genre import router as genre_router
from app.infrastructure.telegram.routers.author.portrait import router as portrait_router
from app.infrastructure.telegram.routers.author.recipient import router as recipient_router
from app.infrastructure.telegram.routers.author.render import render_author_step
from app.infrastructure.telegram.routers.author.summary import (
    render_author_home,
)
from app.infrastructure.telegram.routers.author.summary import (
    router as summary_router,
)

router = Router(name="author")
router.include_router(consent_router)
router.include_router(genre_router)
router.include_router(recipient_router)
router.include_router(portrait_router)
router.include_router(summary_router)

__all__ = ["router", "render_author_home", "render_author_step"]
