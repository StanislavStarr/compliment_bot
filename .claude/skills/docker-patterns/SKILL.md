---
name: docker-patterns
description: Docker и Docker Compose в этом проекте: образ на uv, процессы app/bot/worker/beat/migrate, порядок запуска, безопасность. Использовать при правках Dockerfile, docker-compose.yml, .dockerignore и CI-сборки.
---

# Docker в compliment_bot

Источник правды — `Dockerfile` и `docker-compose.yml` в корне. Этот файл описывает принятые решения, а не заменяет их.

## Образ

- Один образ на все процессы (модульный монолит, ADR-0001 п. 2): `python:3.12-slim`, зависимости ставит `uv` по `uv.lock`.
- Слои для кэша: сначала `pyproject.toml` + `uv.lock` и `uv sync --frozen --no-install-project --no-dev`, затем `app/` и `alembic.ini`.
- Версия `uv` закреплена в `COPY --from=ghcr.io/astral-sh/uv:<версия>`; базовый образ не `latest`.
- Запуск от `appuser` (не root); секреты в образ не копируются (`.env` в `.dockerignore`).
- Dev-зависимости в образ не попадают (`--no-dev`).

## Процессы в Compose

| Сервис | Команда | Роль |
|--------|---------|------|
| `postgres`, `redis` | образы alpine с healthcheck | хранилище и брокер Celery |
| `migrate` | `alembic upgrade head`, `restart: "no"` | разовая миграция перед стартом остальных |
| `app` | uvicorn (CMD образа) | FastAPI: `/health`, `/ready` |
| `bot` | `python -m app.bot_main` | aiogram polling |
| `worker` | `celery -A app.infrastructure.tasks.celery_app worker` | доставка |
| `beat` | `celery -A app.infrastructure.tasks.celery_app beat` | расписание, раз в минуту |

Правила:

- Все сервисы кроме `postgres`/`redis`/`migrate` зависят от `migrate: service_completed_successfully` и от здоровья `redis`.
- Хосты внутри сети задаются через `POSTGRES_HOST`/`REDIS_HOST`; остальная конфигурация приходит из `.env` через `env_file` и читается `Settings`.
- Значения по умолчанию в Compose задаются как `${VAR:-default}` и только для не секретных настроек (порты, имя БД).
- Новый процесс = новый сервис с тем же `build: .` и своим `command`, а не новый образ.
- Новую переменную окружения добавляй одновременно в `config.py`, `.env.example` и, если нужно, в Compose.

## Безопасность

- Пароли и токены не хардкодить в `docker-compose.yml` и `Dockerfile`; `change_me` в `.env.example` и в `:-` — только локальная заглушка.
- Не публиковать порты Postgres/Redis в окружениях вне локальной разработки.
- Опционально для усиления: `security_opt: [no-new-privileges:true]`, `cap_drop: [ALL]` (проверить, что процессы стартуют).

## Команды

```bash
docker compose up --build              # весь стек
docker compose logs -f bot worker      # логи процессов
docker compose run --rm migrate        # повторно применить миграции
docker compose exec postgres psql -U compliment_bot compliment_bot
docker compose down -v                 # остановить и удалить тома (данные БД!)
```

CI (`.github/workflows/ci.yml`, job `docker`) только собирает образ без push; сборка должна оставаться зелёной после правок `Dockerfile`.
