"""Golden tests for employee directory derivations (status, tenure, name).

Pure functions over a row dict — the logic that drives the People screen
and every status filter. Deterministic, no DB.
"""

from datetime import date

import pytest

from app.contexts.core_hr.service import derive_status, full_name, tenure_label

TODAY = date(2026, 6, 13)


def _row(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "is_active": True,
        "date_of_joining": date(2020, 1, 1),
        "date_of_leaving": None,
        "first_name": "Asha",
        "middle_name": None,
        "last_name": "Rao",
    }
    base.update(over)
    return base


class TestDeriveStatus:
    def test_active_default(self) -> None:
        assert derive_status(_row(), TODAY) == "Active"

    def test_notice_when_leaving_today_or_future(self) -> None:
        assert derive_status(_row(date_of_leaving=date(2026, 6, 30)), TODAY) == "Notice"

    def test_joining_when_doj_in_future(self) -> None:
        assert derive_status(_row(date_of_joining=date(2026, 7, 1)), TODAY) == "Joining"

    def test_inactive_when_flag_off(self) -> None:
        assert derive_status(_row(is_active=False), TODAY) == "Inactive"

    def test_inactive_when_already_left(self) -> None:
        assert derive_status(_row(date_of_leaving=date(2026, 5, 1)), TODAY) == "Inactive"

    def test_probation_within_90_days(self) -> None:
        assert derive_status(_row(date_of_joining=date(2026, 5, 1)), TODAY) == "Probation"

    def test_active_just_past_probation(self) -> None:
        # joined 91 days ago
        assert derive_status(_row(date_of_joining=date(2026, 3, 13)), TODAY) == "Active"

    def test_notice_precedes_probation(self) -> None:
        # a recent joiner already serving notice shows Notice, not Probation
        row = _row(date_of_joining=date(2026, 6, 1), date_of_leaving=date(2026, 6, 30))
        assert derive_status(row, TODAY) == "Notice"


class TestTenure:
    @pytest.mark.parametrize(
        "doj,expected",
        [
            (date(2020, 1, 1), "6y 5m"),
            (date(2026, 6, 1), "0y 0m"),
            (date(2025, 6, 13), "1y 0m"),
            (None, "—"),
            (date(2026, 7, 1), "—"),  # future joiner
        ],
    )
    def test_tenure_label(self, doj: date | None, expected: str) -> None:
        assert tenure_label(doj, TODAY) == expected


class TestFullName:
    def test_all_parts(self) -> None:
        assert full_name(_row(middle_name="K")) == "Asha K Rao"

    def test_missing_parts_skipped(self) -> None:
        assert full_name(_row(last_name=None)) == "Asha"

    def test_trims_whitespace(self) -> None:
        assert full_name(_row(first_name=" Asha ", last_name=" Rao ")) == "Asha Rao"
