from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import get_settings
from app.infrastructure.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/ready")
async def ready(response: Response) -> dict[str, Any]:
    checks: dict[str, str] = {}

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["postgres"] = f"error: {exc.__class__.__name__}"

    settings = get_settings()
    redis_client: redis.Redis = redis.from_url(settings.redis_url)  # type: ignore[no-untyped-call]
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc.__class__.__name__}"
    finally:
        await redis_client.aclose()

    is_ready = all(value == "ok" for value in checks.values())
    response.status_code = 200 if is_ready else 503
    return {"status": "ok" if is_ready else "unavailable", "checks": checks}
