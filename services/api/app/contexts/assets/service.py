"""Asset lifecycle rules + straight-line depreciation (pure, Decimal-only)."""

from datetime import date
from decimal import Decimal

from app.core.money import D, Money, round_rupee

# Allowed source states for each transition.
ASSIGNABLE_FROM = frozenset({"in_stock"})
RETURNABLE_FROM = frozenset({"assigned"})
RETIRABLE_FROM = frozenset({"in_stock", "assigned", "lost"})

# Default useful life by category (years) for straight-line book value.
USEFUL_LIFE_YEARS: dict[str, int] = {
    "laptop": 3,
    "desktop": 4,
    "phone": 2,
    "monitor": 5,
    "peripheral": 3,
    "furniture": 7,
    "other": 3,
}
ZERO = D(0)


def can_assign(asset_status: str) -> bool:
    return asset_status in ASSIGNABLE_FROM


def can_return(asset_status: str) -> bool:
    return asset_status in RETURNABLE_FROM


def book_value(
    purchase_cost: Money | None,
    purchase_date: date | None,
    as_of: date,
    *,
    category: str = "other",
) -> Money:
    """Straight-line written-down value, floored at zero (no salvage).

    Depreciates `purchase_cost` evenly over the category's useful life. Returns
    0 once fully depreciated; returns the full cost before the purchase date.
    """
    if purchase_cost is None or purchase_date is None or purchase_cost <= 0:
        return ZERO
    if as_of <= purchase_date:
        return round_rupee(purchase_cost)

    life_years = USEFUL_LIFE_YEARS.get(category, 3)
    life_days = Decimal(life_years * 365)
    elapsed_days = Decimal((as_of - purchase_date).days)
    if elapsed_days >= life_days:
        return ZERO

    remaining_fraction = (life_days - elapsed_days) / life_days
    return round_rupee(purchase_cost * remaining_fraction)
