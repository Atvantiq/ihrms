"""Full-and-Final settlement engine — India (pure, Decimal-only, tested).

Components:
- Gratuity (Payment of Gratuity Act): (15 × last basic × completed years) / 26,
  eligible at >= 5 years, capped at ₹20,00,000. Service >= 6 months in the
  final year rounds the year up.
- Leave encashment: unused leave days × (monthly basic / 26).
- Notice recovery: shortfall days × (monthly gross / 30) when notice not served.
- Net F&F = pending salary + gratuity + leave encashment − notice recovery
  − other recoveries (advances/loans). Tax on settlement is applied separately.

NOT tax advice — statutory caps/rates are versioned (blueprint).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.money import D, round_rupee

GRATUITY_NUMERATOR = D(15)
GRATUITY_DENOMINATOR = D(26)
GRATUITY_MIN_YEARS = 5
GRATUITY_CAP = D(2000000)
ENCASH_DAYS_BASIS = D(26)
NOTICE_DAYS_BASIS = D(30)
ZERO = D(0)


def completed_years(doj: date, lwd: date) -> int:
    """Completed years of service; >= 6 months in the final year rounds up."""
    if lwd < doj:
        return 0
    months = (lwd.year - doj.year) * 12 + (lwd.month - doj.month)
    if lwd.day < doj.day:
        months -= 1
    years, rem = divmod(months, 12)
    return years + 1 if rem >= 6 else years


def gratuity(last_basic: Decimal, doj: date, lwd: date) -> Decimal:
    years = completed_years(doj, lwd)
    if years < GRATUITY_MIN_YEARS:
        return D(0)
    amount = (GRATUITY_NUMERATOR * last_basic * D(years)) / GRATUITY_DENOMINATOR
    return min(round_rupee(amount), GRATUITY_CAP)


def leave_encashment(unused_days: Decimal, monthly_basic: Decimal) -> Decimal:
    if unused_days <= 0:
        return D(0)
    return round_rupee(unused_days * (monthly_basic / ENCASH_DAYS_BASIS))


def notice_recovery(
    notice_required_days: int, notice_served_days: int, monthly_gross: Decimal
) -> Decimal:
    shortfall = max(notice_required_days - notice_served_days, 0)
    if shortfall == 0:
        return D(0)
    return round_rupee(D(shortfall) * (monthly_gross / NOTICE_DAYS_BASIS))


@dataclass(frozen=True)
class FnF:
    pending_salary: Decimal
    gratuity: Decimal
    leave_encashment: Decimal
    notice_recovery: Decimal
    other_recoveries: Decimal

    @property
    def earnings(self) -> Decimal:
        return self.pending_salary + self.gratuity + self.leave_encashment

    @property
    def deductions(self) -> Decimal:
        return self.notice_recovery + self.other_recoveries

    @property
    def net_settlement(self) -> Decimal:
        return self.earnings - self.deductions


def compute_fnf(
    *,
    last_basic: Decimal,
    monthly_gross: Decimal,
    doj: date,
    lwd: date,
    unused_leave_days: Decimal,
    pending_salary: Decimal,
    notice_required_days: int,
    notice_served_days: int,
    other_recoveries: Decimal = ZERO,
) -> FnF:
    return FnF(
        pending_salary=round_rupee(pending_salary),
        gratuity=gratuity(last_basic, doj, lwd),
        leave_encashment=leave_encashment(unused_leave_days, last_basic),
        notice_recovery=notice_recovery(
            notice_required_days, notice_served_days, monthly_gross
        ),
        other_recoveries=round_rupee(other_recoveries),
    )
