# ADR 0001. Базовые архитектурные решения

Статус: принято.

## Контекст

MVP Telegram-бота с ежедневными персонализированными комплиментами/поддержкой.
Полное продуктовое обоснование — в `compliments-bot-product-and-implementation-plan.md`.
Здесь фиксируются только технические решения, чтобы не пересматривать их по ходу разработки.

## Решения

1. **Telegram-бот, а не PWA/Mini App.** Быстрее в разработке, уже есть уведомления и кнопки обратной связи.
2. **Модульный монолит**, один Docker image, несколько процессов: FastAPI+aiogram polling, Celery worker, Celery Beat.
3. **PostgreSQL** — источник истины, идемпотентность через unique constraints. **Redis** — только брокер Celery (+опциональные короткие locks).
4. **Celery + Celery Beat**, один scanner-таск раз в минуту (`dispatch_due_schedules`), без отдельного расписания на пользователя.
5. **Один AI-провайдер за интерфейсом `AIProvider`** (Protocol), без multi-provider fallback на старте. Выбран OpenAI (`gpt-4o-mini`), SDK не импортируется вне `app/infrastructure/ai/providers`.
6. **RAG, embeddings, fine-tuning, своя модель — не используются в MVP.**
7. **Onboarding-состояние хранится в БД** (`users.onboarding_step`), а не в aiogram FSM storage — переживает рестарт процесса без дополнительной инфраструктуры (Redis-backed FSM не требуется).
8. **Структура пакета — `app/` в корне репозитория**, без `src/`-layout. Проект не публикуется как библиотека (`[tool.uv] package = false`), поэтому дополнительный уровень вложенности и packaging-метаданные не нужны. Модульная структура внутри (`domain/application/infrastructure/api`) соответствует продуктовому плану.
9. **Первый проход реализации — только Gift Release**: без `invite_codes`, `access_requests`, ролей `tester`/`admin`, ручной генерации, `/stats`, admin-команд. Критические алерты администратору оставлены (это требование надёжности, не admin-функция) — реализуются как прямая отправка сообщения на `ADMIN_TELEGRAM_ID` из конфига.
10. **Один Compose-стек для локальной разработки.** Разделение на development/production окружения на VPS — отдельный этап после стабилизации Gift Release.

## Последствия

- Добавление invite-системы и ролей в будущем потребует новых таблиц и миграций, но не меняет архитектуру.
- Смена AI-провайдера требует только новой реализации `AIProvider`, без изменений в domain/application слоях.
- Переход на webhook вместо polling потребует отключения background polling в lifespan FastAPI (уже заложено в плане).
