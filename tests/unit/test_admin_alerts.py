from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import SecretStr

from app.config import Settings
from app.infrastructure.monitoring.alerts import AdminAlertService


def _settings(*, admin_id: int | None) -> Settings:
    return Settings(
        telegram_bot_token=SecretStr("test-token"),
        admin_telegram_id=admin_id,
        openai_api_key=SecretStr("test-key"),
    )


async def test_notify_sends_to_admin() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.session.close = AsyncMock()
    service = AdminAlertService(_settings(admin_id=123))

    with patch("app.infrastructure.monitoring.alerts.create_bot", return_value=bot):
        await service.notify("delivery_final_failure", delivery_id="abc")

    bot.send_message.assert_awaited_once()
    assert bot.send_message.await_args.kwargs["chat_id"] == 123
    assert "delivery_final_failure" in bot.send_message.await_args.kwargs["text"]
    bot.session.close.assert_awaited_once()


async def test_notify_skips_without_admin() -> None:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    service = AdminAlertService(_settings(admin_id=None))

    with patch("app.infrastructure.monitoring.alerts.create_bot", return_value=bot):
        await service.notify("delivery_final_failure", delivery_id="abc")

    bot.send_message.assert_not_awaited()
