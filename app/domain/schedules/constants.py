"""Константы диспетчеризации доставок (раздел 17 продуктового плана)."""

from datetime import date

DUE_SCAN_BATCH_SIZE = 100

# Ручные /generate не занимают сегодняшний слот: unique (user_id, local_date).
MANUAL_DELIVERY_DATE_START = date(2099, 1, 1)

DELIVERY_RETRY_DELAYS_SECONDS: list[int] = [60, 300, 900]
DELIVERY_MAX_RETRIES = len(DELIVERY_RETRY_DELAYS_SECONDS)
