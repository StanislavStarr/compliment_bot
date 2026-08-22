from datetime import date

from app.application.admin.service import next_manual_delivery_date
from app.domain.schedules.constants import MANUAL_DELIVERY_DATE_START


def test_first_manual_slot_is_start_date() -> None:
    assert next_manual_delivery_date(None) == MANUAL_DELIVERY_DATE_START


def test_next_slot_follows_latest() -> None:
    assert next_manual_delivery_date(date(2099, 1, 3)) == date(2099, 1, 4)


def test_dates_before_start_are_ignored() -> None:
    assert next_manual_delivery_date(date(2026, 8, 22)) == MANUAL_DELIVERY_DATE_START
