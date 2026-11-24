# CLAUDE.md

Единые правила разработки для Claude Code в этом репозитории. Это единственный источник правды по
архитектуре и принципам; детали по областям лежат в `.claude/rules/`.

## Проект

Telegram-бот, который раз в день присылает персонализированный комплимент или слова поддержки.
Продукт: `compliments-bot-product-and-implementation-plan.md`. Решения: `docs/adr/0001-architecture-decisions.md`.
Если ADR или этот файл противоречат коду, остановись и спроси, а не выбирай молча.

**Стек (зафиксирован, новое не добавлять без согласования):** Python 3.12, aiogram 3, FastAPI (только
`/health` и `/ready`), SQLAlchemy 2.0 async + asyncpg + Alembic, PostgreSQL, Redis (брокер Celery),
Celery + Beat, OpenAI API, structlog, pydantic / pydantic-settings, uv, ruff, mypy, pytest.

## Архитектура

Модульный монолит, слои с однонаправленными зависимостями: `api / infrastructure → application → domain`.

```text
app/
  main.py, bot_main.py, config.py   точки входа (FastAPI; aiogram polling) и Settings
  domain/<area>/                    enums.py, constants.py, чистые правила
  application/<area>/               use-case сервисы (service.py), расчёты, шаги онбординга
  infrastructure/
    db/{models,repositories,migrations}/
    ai/{providers,prompts,validators}/   base.py = Protocol AIProvider
    telegram/{routers,keyboards,middlewares,states}/
    tasks/                          Celery app, scanner, delivery
    logging/, monitoring/
  api/                              FastAPI-роутеры health/ready
tests/{unit,integration}/
```

| Слой | Отвечает за | Нельзя |
|------|-------------|--------|
| `domain` | enums, константы, чистые функции/правила | импортировать что-либо вне `app.domain`, I/O, SQLAlchemy, aiogram |
| `application` | сценарии (use cases), оркестрация репозиториев и AI, **границы транзакций** (`commit` здесь) | aiogram, Celery, тексты и клавиатуры Telegram, SDK OpenAI |
| `infrastructure/db` | модели, репозитории (запросы), миграции | бизнес-правила, `commit` в репозитории |
| `infrastructure/ai` | `AIProvider`, адаптер OpenAI, промпты, валидаторы ответа | SDK OpenAI вне `ai/providers/` |
| `infrastructure/telegram` | роутеры aiogram, клавиатуры, FSM-состояния, тексты UI: разбирает апдейт, вызывает сервис, рендерит ответ | бизнес-логика, прямые SQL-запросы |
| `infrastructure/tasks` | Celery-задачи: тонкая обёртка над сервисами, ретраи доставки | бизнес-логика |
| `api` | HTTP-эндпоинты health/ready | бизнес-логика |

Договорённости, которые уже приняты в коде и сохраняются:

- Сервисы `application` принимают `AsyncSession` и создают нужные репозитории сами; модели и репозитории
  из `infrastructure.db` импортировать в `application` допустимо. Порты/интерфейсы ради интерфейсов не вводим;
  `Protocol` оправдан только там, где есть вторая реализация или внешняя граница (как `AIProvider`).
- Сессию на апдейт открывает `DbSessionMiddleware`, роутеры получают её через `data["session"]`.
- Состояние онбординга хранится в БД (`users.onboarding_step`), не в FSM storage (ADR-0001 п. 7).
- Известные отклонения (роутеры иногда обращаются к репозиториям напрямую) не расширять; новый код
  идёт через сервис. Рефакторить существующее только по прямой просьбе.

### Где что лежит при добавлении фичи

1. Новый enum/константа → `domain/<area>/`.
2. Новая таблица или поле → модель + репозиторий + Alembic-миграция в `infrastructure/db/`.
3. Бизнес-сценарий → `application/<area>/service.py`.
4. Экран/кнопка/команда → `infrastructure/telegram/{routers,keyboards}/`, состояние шага → `states/`.
5. Периодическая или фоновая работа → `infrastructure/tasks/`, логика внутри сервиса.
6. Новая настройка → `config.py` (Pydantic Settings) и `.env.example`.

## Принципы

- **SOLID**: сервис на одну область (SRP); новые варианты поведения добавляются новым кодом, а не
  разрастающимися `if` (OCP); зависимости передаются в конструктор, а не создаются в середине метода.
- **DRY**: повторяется в третий раз и означает одно и то же знание, значит выносим. Совпадение по виду не повод.
- **KISS / YAGNI**: самое простое решение под текущую задачу. Не добавлять базовые классы, фабрики,
  абстракции, библиотеки и параметры «на будущее». Нужна новая зависимость значит спросить.
- **Clean Code**: функции короткие, одна ответственность; имена говорят о намерении; комментарий объясняет
  «почему», а не «что»; нет мёртвого кода и закомментированных кусков; без магических чисел (константы в `domain/*/constants.py`).
- **Минимальный дифф**: делай ровно то, что просили; побочный рефакторинг и «заодно» не делать.

## Команды

```bash
uv sync                                  # зависимости
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest                            # unit; integration требует Postgres и Redis
uv run pytest -m "not integration"
uv run alembic revision --autogenerate -m "<message>"
uv run alembic upgrade head
docker compose up --build                # локальный стек
```

CI (`.github/workflows/ci.yml`): `ruff check`, `ruff format --check`, `mypy .`, сборка Docker. Всё это должно проходить до коммита.

## Правила работы

- **Git: не делать `commit`, `push`, создание веток и PR, пока пользователь явно не попросил.**
- Не менять `.env`, `uv.lock` вручную, применённые миграции; зависимости не ставить без просьбы.
- Любая правка кода: сначала прочитать соседний код и следовать его стилю.
- Поведение меняется вместе с тестом (новая фича, исправленный баг получают тест).
- Перед тем как назвать работу законченной, прогнать `/verify` (или объяснить, что не удалось запустить).
- Язык: документация, комментарии, docstring и тексты бота на русском; идентификаторы, имена коммитов
  (`type: summary`, как в истории) на английском.

## Детальные правила (подгружаются по путям)

| Файл | Область |
|------|---------|
| `.claude/rules/python-style.md` | стиль, типы, логирование, ошибки (`app/**`) |
| `.claude/rules/database.md` | модели, репозитории, транзакции, миграции |
| `.claude/rules/testing.md` | тесты pytest (`tests/**`) |
| `.claude/rules/security.md` | секреты, PII, AI и Telegram-ввод |

## Инструменты Claude Code

- Агенты (`.claude/agents/`): `architect` (дизайн и план фичи), `code-reviewer` (качество, PEP 8, типы,
  SOLID/DRY), `security-reviewer`, `database-reviewer`, `tdd-guide`, `refactor-cleaner` (чистка мёртвого кода и дублей,
  только по явной просьбе).
- Команды (`.claude/commands/`): `/verify`, `/code-review`, `/tdd`.
- Skills (`.claude/skills/`, справочные): `python-patterns`, `python-testing`, `pydantic-patterns`,
  `sqlalchemy-patterns`, `postgres-patterns`, `database-migrations`, `docker-patterns`.
  Если справочник расходится с этим файлом или правилами, приоритет у CLAUDE.md и `rules/`.
- Нового агента, команду или skill добавлять только при повторяющейся потребности; дубли не создавать.
