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

## Docker Compose

Стек: `postgres`, `redis`, `migrate` (одноразовый — накатывает миграции и завершается), `app` (FastAPI), `worker` (Celery worker), `beat` (Celery Beat). `app`/`worker`/`beat` стартуют только после успешного завершения `migrate`.

```bash
# собрать образы и поднять весь стек в фоне
docker compose up -d --build

# поднять без пересборки (если код не менялся)
docker compose up -d

# статус контейнеров
docker compose ps

# логи (добавить -f для follow)
docker compose logs app
docker compose logs worker
docker compose logs beat
docker compose logs migrate

# перезапустить один сервис после изменения кода
docker compose up -d --build app

# зайти в контейнер БД
docker exec -it compliment_bot-postgres-1 psql -U compliment_bot -d compliment_bot

# остановить всё, оставив данные (volumes)
docker compose down

# остановить всё и снести volumes (Postgres/Redis данные удаляются)
docker compose down -v
```

Проверка живости после старта:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
```

## Миграции (Alembic)

В Docker миграции накатываются автоматически сервисом `migrate` при `docker compose up`. Ручные команды нужны для разработки — создание новой миграции и локальных экспериментов.

Локально (используется `.env` с `POSTGRES_HOST=localhost`, поэтому Postgres должен быть доступен на `localhost:5432` — например, через `docker compose up -d postgres`):

```bash
# создать миграцию автоматически по разнице моделей и текущей схемы БД
uv run alembic revision --autogenerate -m "описание изменения"

# создать пустую миграцию (например, для сид-данных)
uv run alembic revision -m "описание"

# накатить все миграции до последней
uv run alembic upgrade head

# накатить только следующую миграцию
uv run alembic upgrade +1

# откатить последнюю миграцию
uv run alembic downgrade -1

# откатить всё (до пустой БД)
uv run alembic downgrade base

# посмотреть текущую версию БД
uv run alembic current

# посмотреть историю миграций
uv run alembic history
```

Внутри уже запущенного Docker-стека (например, чтобы откатить миграцию без пересборки):

```bash
docker compose run --rm migrate alembic downgrade -1
docker compose run --rm migrate alembic upgrade head
docker compose run --rm migrate alembic current
```

После `--autogenerate` всегда открыть файл в `app/infrastructure/db/migrations/versions/` и проверить сгенерированный `upgrade()`/`downgrade()` — автогенерация не видит переименования колонок и не расставляет data-миграции.

## Статус

Разработка ведётся поэтапно по плану из раздела «19. План разработки по этапам» продуктового документа.
Первый проход реализации — Gift Release (без invite-кодов, ролей и admin-команд).
