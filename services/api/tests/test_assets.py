"""Golden tests for asset lifecycle rules + straight-line depreciation."""

from datetime import date

from app.contexts.assets.service import book_value, can_assign, can_return
from app.core.money import D


class TestTransitions:
    def test_only_in_stock_is_assignable(self) -> None:
        assert can_assign("in_stock") is True
        assert can_assign("assigned") is False
        assert can_assign("retired") is False

    def test_only_assigned_is_returnable(self) -> None:
        assert can_return("assigned") is True
        assert can_return("in_stock") is False


class TestBookValue:
    def test_zero_when_no_cost_or_date(self) -> None:
        assert book_value(None, date(2026, 1, 1), date(2026, 6, 1)) == D(0)
        assert book_value(D(50000), None, date(2026, 6, 1)) == D(0)

    def test_full_cost_before_purchase(self) -> None:
        v = book_value(D(60000), date(2026, 6, 1), date(2026, 1, 1), category="laptop")
        assert v == D(60000)

    def test_half_life_is_about_half(self) -> None:
        # laptop life = 3y (1095d); 1.5y in -> ~50% remains
        cost = D(60000)
        v = book_value(cost, date(2024, 1, 1), date(2025, 7, 1), category="laptop")
        # 547 days elapsed of 1095 -> remaining ~ (1095-547)/1095 = 0.5005
        assert D(29000) < v < D(31000)

    def test_fully_depreciated_is_zero(self) -> None:
        v = book_value(D(60000), date(2020, 1, 1), date(2026, 1, 1), category="laptop")
        assert v == D(0)

    def test_longer_life_depreciates_slower(self) -> None:
        d0, asof = date(2024, 1, 1), date(2025, 1, 1)
        phone = book_value(D(60000), d0, asof, category="phone")      # 2y life
        furniture = book_value(D(60000), d0, asof, category="furniture")  # 7y life
        assert furniture > phone
