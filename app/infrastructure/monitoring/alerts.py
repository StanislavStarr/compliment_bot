import html

from app.config import Settings
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.telegram.bot import create_bot

logger = get_logger(__name__)


class AdminAlertService:
    """Критические сбои (final failure доставки) уходят админу в Telegram.
    Нет ADMIN_TELEGRAM_ID — только лог, без исключения наружу."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def notify(self, event: str, **fields: object) -> None:
        payload = {key: str(value) for key, value in fields.items()}
        logger.error(event, **payload)

        admin_id = self._settings.admin_telegram_id
        if admin_id is None:
            logger.warning("admin_alert_skipped_no_admin", alert_event=event)
            return
        if not self._settings.telegram_bot_token.get_secret_value():
            logger.warning("admin_alert_skipped_no_token", alert_event=event)
            return

        lines = [f"<b>{html.escape(event)}</b>"]
        lines.extend(f"{html.escape(key)}: {html.escape(value)}" for key, value in payload.items())
        bot = create_bot(self._settings)
        try:
            await bot.send_message(chat_id=admin_id, text="\n".join(lines))
        except Exception as exc:
            logger.error("admin_alert_failed", alert_event=event, error=str(exc))
        finally:
            await bot.session.close()
