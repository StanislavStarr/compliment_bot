# Compliment Bot

Telegram-бот, который раз в день присылает короткий персонализированный комплимент или слова поддержки на основе профиля пользователя, выбранных тем и накопленной обратной связи.

Продуктовый и технический план: [`compliments-bot-product-and-implementation-plan.md`](./compliments-bot-product-and-implementation-plan.md).
Архитектурные решения: [`docs/adr/0001-architecture-decisions.md`](./docs/adr/0001-architecture-decisions.md).

## Стек

Python 3.12, aiogram 3.x, FastAPI, SQLAlchemy (async) + Alembic, PostgreSQL, Redis, Celery + Celery Beat, OpenAI API, Docker Compose. Управление зависимостями — [`uv`](https://docs.astral.sh/uv/).

## Структура проекта

```text
app/
  main.py                 # точка входа FastAPI + запуск aiogram polling
  config.py                # конфиг на Pydantic Settings

  domain/                  # сущности и бизнес-правила, без внешних зависимостей
    users/ profiles/ schedules/ messages/ feedback/

  application/              # сценарии use-case, работают через интерфейсы
    onboarding/ generation/ scheduling/ feedback/ settings/

  infrastructure/
    db/                      # SQLAlchemy models, repositories, Alembic migrations
    ai/                      # AIProvider, адаптер OpenAI, промпты, валидаторы
    telegram/                # aiogram routers, keyboards, middlewares, FSM states
    tasks/                   # Celery app, scheduler, delivery task
    logging/
    monitoring/

  api/
    health.py ready.py

tests/
  unit/ integration/ fixtures/
```

## Разработка

```bash
# установить зависимости
uv sync

# запустить линтер / форматирование / типы
uv run ruff check .
uv run ruff format .
uv run mypy .

# тесты
uv run pytest

# pre-commit хуки
uv run pre-commit install
```

Переменные окружения — см. [`.env.example`](./.env.example), скопировать в `.env` и заполнить токен бота и ключ OpenAI.

## Статус

Разработка ведётся поэтапно по плану из раздела «19. План разработки по этапам» продуктового документа.
Первый проход реализации — Gift Release (без invite-кодов, ролей и admin-команд).
