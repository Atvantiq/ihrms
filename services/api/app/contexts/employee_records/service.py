"""Pure helpers for employee personal records (Employee 360 sub-tabs).

Special dates (birthday / work anniversary) are *derived* from DOB / DOJ rather
than stored — given a reference date we project the next occurrence and the days
until it. Nominee shares are validated to never exceed 100% across a family set.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

ZERO = Decimal(0)


@dataclass(frozen=True)
class SpecialDate:
    label: str
    on: date          # the next occurrence (this year or next)
    in_days: int
    years: int | None  # completed years at the next occurrence (None for birthday age hidden)


def _next_anniversary(anchor: date, today: date) -> date:
    """The next month/day occurrence of `anchor` on/after `today`."""
    year = today.year
    try:
        candidate = anchor.replace(year=year)
    except ValueError:  # Feb 29 anchor in a non-leap year -> use Mar 1
        candidate = date(year, 3, 1)
    if candidate < today:
        try:
            candidate = anchor.replace(year=year + 1)
        except ValueError:
            candidate = date(year + 1, 3, 1)
    return candidate


def special_dates(
    date_of_birth: date | None,
    date_of_joining: date | None,
    today: date,
) -> list[SpecialDate]:
    """Project upcoming birthday and work anniversary from DOB / DOJ."""
    out: list[SpecialDate] = []
    if date_of_birth is not None:
        nxt = _next_anniversary(date_of_birth, today)
        out.append(SpecialDate("Birthday", nxt, (nxt - today).days, None))
    if date_of_joining is not None:
        nxt = _next_anniversary(date_of_joining, today)
        years = nxt.year - date_of_joining.year
        out.append(SpecialDate("Work anniversary", nxt, (nxt - today).days, years))
    return sorted(out, key=lambda s: s.in_days)


def nominee_total_ok(existing_shares: list[Decimal], new_share: Decimal) -> bool:
    """True when adding `new_share` keeps the nominee total within 100%."""
    return sum(existing_shares, ZERO) + new_share <= Decimal(100)
