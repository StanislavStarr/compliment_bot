---
description: Полная проверка проекта: ruff, формат, mypy, pytest. Аргумент quick пропускает тесты.
---

# /verify

Выполни по порядку и сообщи результат по каждому шагу (при ошибке покажи `file:line`, но НЕ чини без просьбы):

1. `uv run ruff check .`
2. `uv run ruff format --check .`
3. `uv run mypy .`
4. `uv run pytest -m "not integration"` (пропусти, если `$ARGUMENTS` = `quick`)
5. Поиск отладочного мусора в изменённых файлах: `print(`, `breakpoint()`, `pdb`.

Integration-тесты требуют Postgres и Redis: запускай `uv run pytest` целиком, только если они подняты.
Если какой-то шаг не удалось выполнить (нет окружения/сети), напиши это явно.

Формат итога:

```
Ruff: OK | N проблем
Format: OK | N файлов
Mypy: OK | N ошибок
Tests: X passed, Y failed, Z skipped
Debug: OK | найдено
Итог: PASS | FAIL
```
