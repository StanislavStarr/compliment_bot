import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import InlineKeyboardMarkup
from celery import Task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.generation.service import GenerationService
from app.application.scheduling.calculator import compute_next_run_after
from app.config import Settings, get_settings
from app.domain.schedules.constants import DELIVERY_MAX_RETRIES, DELIVERY_RETRY_DELAYS_SECONDS
from app.domain.schedules.enums import MISSED_DELIVERY_THRESHOLD_HOURS, DeliveryStatus
from app.domain.users.enums import UserStatus
from app.infrastructure.ai.base import AIProviderError
from app.infrastructure.ai.factory import create_ai_provider
from app.infrastructure.ai.prompts.builder import build_system_prompt
from app.infrastructure.db.models.deliveries import Delivery
from app.infrastructure.db.models.messages import GeneratedMessage
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.deliveries import DeliveryRepository
from app.infrastructure.db.repositories.messages import GeneratedMessageRepository
from app.infrastructure.db.repositories.prompt_versions import PromptVersionRepository
from app.infrastructure.db.repositories.schedules import ScheduleRepository
from app.infrastructure.db.repositories.users import UserRepository
from app.infrastructure.db.session import get_celery_session_factory
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.telegram.bot import create_bot
from app.infrastructure.telegram.keyboards.feedback import feedback_keyboard

logger = get_logger(__name__)

_TERMINAL_STATUSES = {DeliveryStatus.SENT, DeliveryStatus.EXPIRED, DeliveryStatus.FAILED}


class TransientDeliveryError(Exception):
    """Временная ошибка AI или Telegram — таск должен ретраиться на уровне
    Celery (раздел 17 плана: 1 / 5 / 15 минут)."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class PermanentDeliveryError(Exception):
    """Не имеет смысла ретраить (бот заблокирован, некорректный chat_id и т.п.)."""

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


def _retry_countdown(retries: int) -> int:
    index = min(retries, len(DELIVERY_RETRY_DELAYS_SECONDS) - 1)
    return DELIVERY_RETRY_DELAYS_SECONDS[index]


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True, name="tasks.deliver_message", max_retries=DELIVERY_MAX_RETRIES
)
def deliver_message_task(self: Task, delivery_id: str) -> None:
    try:
        asyncio.run(_deliver_message(uuid.UUID(delivery_id)))
    except TransientDeliveryError as exc:
        countdown = exc.retry_after or _retry_countdown(self.request.retries)
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.warning(
                "delivery_retries_exhausted",
                delivery_id=delivery_id,
                retries=self.request.retries,
                error=str(exc),
            )
            asyncio.run(_finalize_after_exhausted_retries(uuid.UUID(delivery_id)))


async def _deliver_message(delivery_id: uuid.UUID) -> None:
    """Один прогон доставки. Может быть вызван повторно Celery-retry'ем —
    при повторном вызове с уже сгенерированным сообщением AI не вызывается
    заново, отправляется тот же сохранённый текст."""
    settings = get_settings()
    async with get_celery_session_factory()() as session:
        delivery_repo = DeliveryRepository(session)
        delivery = await delivery_repo.get_for_update(delivery_id)
        if delivery is None:
            logger.warning("delivery_not_found", delivery_id=str(delivery_id))
            return
        if delivery.status in _TERMINAL_STATUSES:
            return

        now = datetime.now(UTC)
        if now - delivery.planned_at_utc > timedelta(hours=MISSED_DELIVERY_THRESHOLD_HOURS):
            await delivery_repo.mark_expired(delivery)
            await _advance_schedule(session, delivery)
            await session.commit()
            logger.warning("delivery_expired_missed_threshold", delivery_id=str(delivery_id))
            return

        user = await UserRepository(session).get_by_id(delivery.user_id)
        if user is None or user.status == UserStatus.BLOCKED:
            await delivery_repo.mark_failed(delivery, "user_unavailable")
            await session.commit()
            return

        await delivery_repo.record_attempt(delivery)
        await session.commit()

        try:
            provider = create_ai_provider(settings)
            service = GenerationService(session, provider)
            message = await _generate_message(session, service, user, delivery, allow_ai=True)
            await _send_and_finalize(session, settings, user, delivery, message)
        except (TransientDeliveryError, PermanentDeliveryError):
            raise
        except Exception as exc:
            # Любая непредвиденная ошибка (например, невалидный/отсутствующий
            # OPENAI_API_KEY при создании клиента — эта ошибка вылетает ДО
            # AIProviderError и раньше вообще не ловилась) не должна навсегда
            # "подвешивать" доставку в QUEUED — иначе next_run_at_utc никогда
            # не продвинется и расписание перестанет работать.
            logger.error(
                "delivery_unexpected_error",
                delivery_id=str(delivery_id),
                error=f"{exc.__class__.__name__}: {exc}",
            )
            raise TransientDeliveryError(f"unexpected_error: {exc}") from exc


async def _finalize_after_exhausted_retries(delivery_id: uuid.UUID) -> None:
    """AI failure пункт 3: "после исчерпания API retries → fallback".
    Если и отправка fallback не удаётся — пункт 6: "final failure и alert"
    (алертинг как отдельный канал — Этап 7, здесь пишем ERROR-лог)."""
    settings = get_settings()
    async with get_celery_session_factory()() as session:
        delivery_repo = DeliveryRepository(session)
        delivery = await delivery_repo.get_for_update(delivery_id)
        if delivery is None or delivery.status in _TERMINAL_STATUSES:
            return

        user = await UserRepository(session).get_by_id(delivery.user_id)
        if user is None or user.status == UserStatus.BLOCKED:
            await delivery_repo.mark_failed(delivery, "user_unavailable")
            await session.commit()
            return

        try:
            provider = create_ai_provider(settings)
            service = GenerationService(session, provider)
            message = await _generate_message(session, service, user, delivery, allow_ai=False)
            await _send_and_finalize(session, settings, user, delivery, message)
        except PermanentDeliveryError:
            pass
        except Exception as exc:
            # Сюда же попадает GenerationError (нет резервных сообщений для
            # темы) и любая другая неожиданная ошибка — это последняя попытка
            # для данной доставки, дальше только failed + продвижение
            # расписания, чтобы не заблокировать следующие дни.
            await delivery_repo.mark_failed(delivery, "final_failure")
            await _advance_schedule(session, delivery)
            await session.commit()
            logger.error("delivery_final_failure", delivery_id=str(delivery_id), error=str(exc))


async def _generate_message(
    session: AsyncSession,
    service: GenerationService,
    user: User,
    delivery: Delivery,
    *,
    allow_ai: bool,
) -> GeneratedMessage:
    """Генерация происходит не более одного раза за жизненный цикл delivery:
    если сообщение для неё уже сохранено (предыдущая попытка дошла до этого
    шага, но упала на отправке в Telegram), просто возвращаем его —
    "Telegram retry не должен создавать новое сообщение" (раздел 17)."""
    generated_repo = GeneratedMessageRepository(session)
    existing = await generated_repo.get_by_delivery_id(delivery.id)
    if existing is not None:
        return existing

    delivery_repo = DeliveryRepository(session)
    await delivery_repo.mark_generating(delivery)
    await session.commit()

    if allow_ai:
        try:
            outcome = await service.generate_via_ai_or_raise(user)
        except AIProviderError as exc:
            await delivery_repo.record_attempt(delivery, "ai_provider_error")
            await session.commit()
            raise TransientDeliveryError(f"ai_provider_error: {exc}") from exc
    else:
        outcome = await service.generate_fallback_only(user)

    prompt_version_id = None
    if outcome.prompt_version:
        prompt_version = await PromptVersionRepository(session).get_or_create(
            outcome.prompt_version, build_system_prompt()
        )
        prompt_version_id = prompt_version.id

    message = await generated_repo.create(
        delivery_id=delivery.id,
        user_id=user.id,
        text=outcome.text,
        message_type=outcome.message_type,
        theme=outcome.theme,
        semantic_key=outcome.semantic_key,
        source=outcome.source,
        generated_at=datetime.now(UTC),
        provider=outcome.provider,
        model=outcome.model,
        prompt_version_id=prompt_version_id,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        total_tokens=outcome.total_tokens,
        validation_status=outcome.validation_status,
    )
    await delivery_repo.mark_ready(delivery)
    await session.commit()
    return message


async def _send_and_finalize(
    session: AsyncSession,
    settings: Settings,
    user: User,
    delivery: Delivery,
    message: GeneratedMessage,
) -> None:
    delivery_repo = DeliveryRepository(session)
    generated_repo = GeneratedMessageRepository(session)

    await delivery_repo.mark_sending(delivery)
    await session.commit()

    bot = create_bot(settings)
    try:
        assert message.text is not None
        await _send_telegram_message(
            bot, user, message.text, reply_markup=feedback_keyboard(message.id)
        )
    except PermanentDeliveryError as exc:
        if exc.error_code == "telegram_forbidden":
            await UserRepository(session).mark_blocked(user)
            schedule_repo = ScheduleRepository(session)
            schedule = await schedule_repo.get_by_user_id(user.id)
            if schedule is not None:
                await schedule_repo.pause(schedule)
        await delivery_repo.mark_failed(delivery, exc.error_code)
        await _advance_schedule(session, delivery)
        await session.commit()
        logger.warning(
            "delivery_permanent_failure", delivery_id=str(delivery.id), error_code=exc.error_code
        )
        return
    finally:
        await bot.session.close()

    await delivery_repo.mark_sent(delivery)
    await generated_repo.mark_sent(message)
    await _advance_schedule(session, delivery)
    await session.commit()
    logger.info("delivery_sent", delivery_id=str(delivery.id))


async def _send_telegram_message(
    bot: Bot, user: User, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    try:
        await bot.send_message(chat_id=user.telegram_chat_id, text=text, reply_markup=reply_markup)
    except TelegramForbiddenError as exc:
        raise PermanentDeliveryError("telegram_forbidden") from exc
    except TelegramBadRequest as exc:
        raise PermanentDeliveryError("telegram_bad_request") from exc
    except TelegramRetryAfter as exc:
        raise TransientDeliveryError(
            f"telegram_retry_after: {exc}", retry_after=exc.retry_after
        ) from exc
    except (TelegramNetworkError, TelegramServerError) as exc:
        raise TransientDeliveryError(f"telegram_network_error: {exc}") from exc
    except TelegramAPIError as exc:
        raise TransientDeliveryError(f"telegram_api_error: {exc}") from exc


async def _advance_schedule(session: AsyncSession, delivery: Delivery) -> None:
    """Раздел 17: "После каждой завершённой доставки рассчитывается
    следующее локальное время" — вызывается для sent/expired/failed, чтобы
    расписание не осталось навсегда "due" и не заблокировало все следующие
    дни. Не трогает расписания, уже поставленные на паузу (Forbidden)."""
    schedule_repo = ScheduleRepository(session)
    schedule = await schedule_repo.get_by_user_id(delivery.user_id)
    if schedule is None or not schedule.is_active:
        return

    next_run_at_utc = compute_next_run_after(
        delivery.local_delivery_date,
        datetime.now(UTC),
        schedule.timezone_name,
        schedule.mode,
        schedule.exact_local_time,
        schedule.period,
    )
    await schedule_repo.mark_sent(schedule, delivery.local_delivery_date, next_run_at_utc)
