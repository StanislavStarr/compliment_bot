from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Проверяет только то, что процесс жив. Без обращения к внешним сервисам."""
    return {"status": "ok"}
