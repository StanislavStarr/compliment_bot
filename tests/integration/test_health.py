from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_dependency_checks() -> None:
    """/ready не должен падать даже если Postgres/Redis недоступны локально —
    он обязан вернуть структурированный отчёт о состоянии зависимостей.
    Полная проверка с реальными Postgres/Redis добавляется в Этапе 7."""
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code in (200, 503)
    body = response.json()
    assert set(body["checks"]) == {"postgres", "redis"}
