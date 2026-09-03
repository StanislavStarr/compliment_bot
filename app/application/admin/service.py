from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.generation.service import GenerationError, GenerationService
from app.domain.schedules.constants import MANUAL_DELIVERY_DATE_START
from app.infrastructure.ai.base import AIProvider
from app.infrastructure.ai.prompts.builder import build_system_prompt
from app.infrastructure.db.models.deliveries import Delivery
from app.infrastructure.db.models.messages import GeneratedMessage
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.deliveries import DeliveryRepository
from app.infrastructure.db.repositories.messages import GeneratedMessageRepository
from app.infrastructure.db.repositories.prompt_versions import PromptVersionRepository
from app.infrastructure.db.repositories.schedules import ScheduleRepository


class ManualDeliveryError(Exception):
    pass


def next_manual_delivery_date(
    latest: date | None, start: date = MANUAL_DELIVERY_DATE_START
) -> date:
    """Следующая свободная тестовая дата, не пересекающаяся с плановым слотом."""
    if latest is None or latest < start:
        return start
    return latest + timedelta(days=1)


class ManualDeliveryService:
    """Внеплановая доставка (/generate и первое сообщение после онбординга):
    тот же persist, что у worker, без сдвига next_run."""

    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._session = session
        self.generation = GenerationService(session, provider)
        self.deliveries = DeliveryRepository(session)
        self.messages = GeneratedMessageRepository(session)
        self.schedules = ScheduleRepository(session)
        self.prompt_versions = PromptVersionRepository(session)

    async def create_and_generate(self, user: User) -> tuple[Delivery, GeneratedMessage]:
        schedule = await self.schedules.get_by_user_id(user.id)
        if schedule is None:
            raise ManualDeliveryError("сначала завершите настройку расписания")

        latest = await self.deliveries.latest_local_date_on_or_after(
            user.id, MANUAL_DELIVERY_DATE_START
        )
        local_date = next_manual_delivery_date(latest)
        now = datetime.now(UTC)
        delivery, created = await self.deliveries.get_or_create(
            user_id=user.id,
            schedule_id=schedule.id,
            local_delivery_date=local_date,
            planned_at_utc=now,
            idempotency_key=f"manual:{user.id}:{local_date.isoformat()}",
        )
        if not created:
            raise ManualDeliveryError("не удалось зарезервировать тестовый слот, повторите")

        await self.deliveries.mark_generating(delivery)
        await self._session.commit()

        try:
            outcome = await self.generation.generate(user)
        except GenerationError as exc:
            await self.deliveries.mark_failed(delivery, "generation_error")
            await self._session.commit()
            raise ManualDeliveryError(str(exc)) from exc

        prompt_version_id = None
        if outcome.prompt_version:
            prompt_version = await self.prompt_versions.get_or_create(
                outcome.prompt_version, build_system_prompt()
            )
            prompt_version_id = prompt_version.id

        message = await self.messages.create(
            delivery_id=delivery.id,
            user_id=user.id,
            text=outcome.text,
            message_type=outcome.message_type,
            theme=outcome.theme,
            semantic_key=outcome.semantic_key,
            source=outcome.source,
            generated_at=now,
            provider=outcome.provider,
            model=outcome.model,
            prompt_version_id=prompt_version_id,
            input_tokens=outcome.input_tokens,
            output_tokens=outcome.output_tokens,
            total_tokens=outcome.total_tokens,
            validation_status=outcome.validation_status,
        )
        await self.deliveries.mark_ready(delivery)
        await self._session.commit()
        return delivery, message

    async def mark_sent(self, delivery: Delivery, message: GeneratedMessage) -> None:
        await self.deliveries.mark_sending(delivery)
        await self.deliveries.mark_sent(delivery)
        await self.messages.mark_sent(message)
        await self._session.commit()

    async def mark_failed(self, delivery: Delivery, error_code: str) -> None:
        await self.deliveries.mark_failed(delivery, error_code)
        await self._session.commit()
