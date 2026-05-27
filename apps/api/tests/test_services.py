from datetime import date

from app.services import next_date_for_recurrence


def test_next_date_weekly():
    assert next_date_for_recurrence(date(2026, 5, 27), "weekly") == date(2026, 6, 3)


def test_next_date_monthly():
    assert next_date_for_recurrence(date(2026, 1, 31), "monthly") == date(2026, 2, 28)
