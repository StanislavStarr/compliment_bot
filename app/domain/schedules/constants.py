"""Константы диспетчеризации доставок (раздел 17 продуктового плана)."""

DUE_SCAN_BATCH_SIZE = 100

DELIVERY_RETRY_DELAYS_SECONDS: list[int] = [60, 300, 900]
DELIVERY_MAX_RETRIES = len(DELIVERY_RETRY_DELAYS_SECONDS)
