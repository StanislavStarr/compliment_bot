---
paths:
  - "app/**/*.py"
  - "scripts/**/*.py"
---
# Python: стиль и качество

Конфигурация инструментов — в `pyproject.toml` (источник правды): ruff (`E,F,W,I,UP,B,SIM,C4,ASYNC`),
`ruff format`, длина строки 100, mypy `strict`. Black, isort, pylint, flake8 не используем.

- PEP 8; импорты сортирует ruff (`app` — first-party). Код обязан проходить `ruff check`, `ruff format --check`, `mypy .`.
- Аннотации типов на всех функциях и методах. Синтаксис 3.12: `list[str]`, `X | None`, без `typing.List/Optional`.
  `Any` только на границе с внешними библиотеками.
- `is None` / `is not None`; без голого `except:`; ловить конкретные исключения. Доменные ошибки — свои
  классы (как `OrderError`, `OpenOrderExistsError`), не `ValueError` на всё подряд.
- Логи: `get_logger(__name__)` из `app.infrastructure.logging.setup` (structlog), события вида
  `logger.info("event_name", key=value)`. Никаких `print()`. В логи не попадают токены, ключи и тексты сообщений пользователей.
- Конфиг только через `app.config.get_settings()`; `os.environ` в коде не читать.
- Неизменяемое по умолчанию для данных без поведения: `@dataclass(frozen=True)`, `NamedTuple`, `tuple`.
- `pathlib.Path` вместо `os.path`; f-строки; `datetime` всегда timezone-aware (UTC).
- Функция делает одно дело и умещается на экране; ранний возврат вместо глубокой вложенности;
  вынесение общего кода — по правилу из CLAUDE.md (DRY на третьем повторении).
- Асинхронный код не блокирует цикл: без `time.sleep`, `requests`, синхронных вызовов БД и SDK.
- Комментарии и docstring на русском, объясняют «почему». Мёртвый код и закомментированные блоки удалять.
- Справочник идиом: skill `python-patterns` (при расхождении приоритет у этого файла).
