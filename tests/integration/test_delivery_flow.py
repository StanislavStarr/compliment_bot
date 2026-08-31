from datetime import UTC, datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
import redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.onboarding.service import OnboardingService
from app.application.scheduling.scanner import collect_due_delivery_ids
from app.application.settings.service import SettingsService
from app.config import get_settings
from app.domain.schedules.enums import DeliveryStatus, ScheduleMode
from app.domain.users.enums import AddressMode, OnboardingStep, UserStatus
from app.infrastructure.ai.base import AIGenerationResult, GenerationRequest
from app.infrastructure.db.models.deliveries import Delivery
from app.infrastructure.db.models.messages import GeneratedMessage
from app.infrastructure.db.repositories.topics import TopicRepository
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.tasks.delivery import _deliver_message

TEST_TELEGRAM_USER_ID = 9_001_001_001
TEST_TELEGRAM_CHAT_ID = 9_001_001_002

VALID_TEXT = (
    "Ты умеешь находить тепло даже в самых обычных днях, и это по-настоящему ценно, "
    "ведь такое качество редко встречается."
)


class _ScriptedProvider:
    async def generate_message(self, request: GenerationRequest) -> AIGenerationResult:
        return AIGenerationResult(
            text=VALID_TEXT,
            message_type=request.message_type,
            theme=request.topic_code,
            semantic_key="тепло в обычных днях",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
        )


async def _session_or_skip() -> AsyncSession:
    try:
        session = get_session_factory()()
        await session.execute(text("select 1 from topics limit 1"))
    except Exception as exc:
        pytest.skip(f"Нет Postgres со схемой бота: {exc}")
    return session


def _redis_or_skip() -> None:
    try:
        client = redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        client.ping()
        client.close()
    except Exception as exc:
        pytest.skip(f"Redis недоступен: {exc}")


@pytest.mark.integration
async def test_due_scan_delivers_once_and_delete_cascades() -> None:
    _redis_or_skip()
    session = await _session_or_skip()
    onboarding = OnboardingService(session)
    user = None
    try:
        existing = await onboarding.users.get_by_telegram_id(TEST_TELEGRAM_USER_ID)
        if existing is not None:
            await onboarding.users.delete(existing)
            await session.commit()

        user = await onboarding.get_or_create_user(TEST_TELEGRAM_USER_ID, TEST_TELEGRAM_CHAT_ID)
        user.address_mode = AddressMode.INFORMAL
        user.status = UserStatus.ACTIVE
        user.onboarding_step = OnboardingStep.DONE
        topics = await TopicRepository(session).list_all()
        if not topics:
            pytest.skip("каталог тем пуст — нужны миграции с seed")
        await onboarding.user_topics.replace_for_user(user.id, [topics[0].id])
        await onboarding.schedules.upsert(
            user_id=user.id,
            mode=ScheduleMode.EXACT,
            timezone_name="UTC",
            next_run_at_utc=datetime(2026, 8, 22, 10, 0, tzinfo=UTC),
            exact_local_time=time(10, 0),
        )
        await session.commit()

        now = datetime(2026, 8, 22, 10, 1, tzinfo=UTC)
        created = await collect_due_delivery_ids(session, now)
        await session.commit()
        assert len(created) == 1
        delivery_id = UUID(created[0])

        created_again = await collect_due_delivery_ids(session, now)
        await session.commit()
        assert created_again == []

        sent: list[dict[str, object]] = []

        async def fake_send(
            bot: object, target_user: object, text: str, reply_markup: object = None
        ) -> None:
            sent.append({"text": text, "reply_markup": reply_markup})

        fake_bot = SimpleNamespace(session=SimpleNamespace(close=AsyncMock()))
        with (
            patch(
                "app.infrastructure.tasks.delivery.create_ai_provider",
                return_value=_ScriptedProvider(),
            ),
            patch("app.infrastructure.tasks.delivery.create_bot", return_value=fake_bot),
            patch(
                "app.infrastructure.tasks.delivery._send_telegram_message",
                side_effect=fake_send,
            ),
        ):
            await _deliver_message(delivery_id)

        session.expire_all()
        delivery = await session.get(Delivery, delivery_id)
        assert delivery is not None
        assert delivery.status is DeliveryStatus.SENT
        message_result = await session.execute(
            select(GeneratedMessage).where(GeneratedMessage.delivery_id == delivery_id)
        )
        message = message_result.scalar_one()
        assert message.text == VALID_TEXT
        assert sent and sent[0]["text"] == VALID_TEXT

        user_id = user.id
        await SettingsService(session).delete_account(user)
        user = None

        leftover = await session.execute(
            select(func.count()).select_from(Delivery).where(Delivery.user_id == user_id)
        )
        assert leftover.scalar_one() == 0
        leftover_messages = await session.execute(
            select(func.count())
            .select_from(GeneratedMessage)
            .where(GeneratedMessage.user_id == user_id)
        )
        assert leftover_messages.scalar_one() == 0
    finally:
        if user is not None:
            await OnboardingService(session).users.delete(user)
            await session.commit()
        await session.close()
