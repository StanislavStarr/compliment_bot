---
paths:
  - "app/infrastructure/db/**/*.py"
  - "app/application/**/*.py"
---
# База данных (PostgreSQL + SQLAlchemy 2.0 async)

- Стиль 2.0: `select()`, `AsyncSession`; legacy `Query` не использовать. Только параметризованные запросы, без f-строк в SQL.
- Модель наследует `Base, UUIDPkMixin, TimestampMixin` (`db/base.py`): первичные ключи UUID, время timezone-aware.
  Enum-типы берутся из `app.domain.*`.
- Репозиторий: один класс на агрегат в `db/repositories/`, принимает `AsyncSession`, методы названы по
  намерению (`get_open_for_author`), **не делает `commit`** (допустим `flush`). Общий `BaseRepository` не вводить.
- Границы транзакций — в сервисах `application`: сервис вызывает `commit()` после завершённого сценария.
  Роутеры и Celery-задачи сами бизнес-транзакции не собирают.
- Связанные данные грузить явно (`selectinload`/`joinedload`), не допускать N+1 в циклах.
- Явные колонки и условия; выборки без лимита по растущим таблицам не делать; для списков — keyset (курсор), не `OFFSET`.
- Внешние ключи индексировать; ограничения целостности (`unique`, `nullable=False`, FK) описывать в модели и миграции.
- Миграции: Alembic, каталог `app/infrastructure/db/migrations/versions/`. Правила:
  - одна миграция — одно логическое изменение, обязательно рабочий `downgrade`;
  - автогенерацию проверять глазами, применённые миграции не править;
  - изменение данных (backfill) отдельным шагом; для необратимых изменений — expand → migrate → contract;
  - при добавлении enum-значений проверять, что миграция их действительно создаёт.
- Справочники: `sqlalchemy-patterns`, `postgres-patterns`, `database-migrations` (при расхождении приоритет у этого файла).
