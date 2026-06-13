"""Golden tests for comp-off validity rules."""

from datetime import date

from app.contexts.comp_off.service import VALIDITY_DAYS, expiry_for, is_expired


class TestExpiry:
    def test_expiry_is_90_days_after_earned(self) -> None:
        assert VALIDITY_DAYS == 90
        assert expiry_for(date(2026, 4, 1)) == date(2026, 6, 30)

    def test_not_expired_before_expiry(self) -> None:
        exp = expiry_for(date(2026, 4, 1))
        assert is_expired(exp, date(2026, 6, 1)) is False

    def test_expired_after_expiry(self) -> None:
        exp = expiry_for(date(2026, 4, 1))
        assert is_expired(exp, date(2026, 7, 15)) is True

    def test_on_expiry_day_not_expired(self) -> None:
        exp = expiry_for(date(2026, 4, 1))
        assert is_expired(exp, exp) is False

    def test_none_expiry_never_expired(self) -> None:
        assert is_expired(None, date(2026, 7, 15)) is False
