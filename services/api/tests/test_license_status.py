"""Golden tests for license renewal-status classification."""

from datetime import date

from app.contexts.assets.service import license_renewal_status

TODAY = date(2026, 6, 13)


def test_none_when_no_date() -> None:
    assert license_renewal_status(None, TODAY) == "none"


def test_expired() -> None:
    assert license_renewal_status(date(2026, 6, 12), TODAY) == "expired"


def test_expiring_within_30_days() -> None:
    assert license_renewal_status(TODAY, TODAY) == "expiring"          # 0 days
    assert license_renewal_status(date(2026, 7, 13), TODAY) == "expiring"  # 30 days


def test_active_beyond_30_days() -> None:
    assert license_renewal_status(date(2026, 7, 14), TODAY) == "active"  # 31 days
