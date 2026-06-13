"""Payroll run outputs — statutory totals and the GL journal (pure, tested).

Operate on a list of payslip dicts (earnings / deductions /
employer_contributions as Decimal maps, plus gross / net).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.core.money import D, Money


@dataclass(frozen=True)
class StatutoryTotals:
    pf_employee: Money
    pf_employer: Money
    esi_employee: Money
    esi_employer: Money
    pt: Money
    tds: Money

    @property
    def pf_total(self) -> Money:
        return self.pf_employee + self.pf_employer

    @property
    def esi_total(self) -> Money:
        return self.esi_employee + self.esi_employer


def _sum(payslips: list[dict[str, Any]], bucket: str, key: str) -> Money:
    total = D(0)
    for p in payslips:
        total += Decimal(str(p[bucket].get(key, 0)))
    return total


def statutory_totals(payslips: list[dict[str, Any]]) -> StatutoryTotals:
    return StatutoryTotals(
        pf_employee=_sum(payslips, "deductions", "pf_employee"),
        pf_employer=_sum(payslips, "employer_contributions", "pf_employer"),
        esi_employee=_sum(payslips, "deductions", "esi_employee"),
        esi_employer=_sum(payslips, "employer_contributions", "esi_employer"),
        pt=_sum(payslips, "deductions", "pt"),
        tds=_sum(payslips, "deductions", "tds"),
    )


@dataclass(frozen=True)
class JournalLine:
    account: str
    debit: Money = D(0)
    credit: Money = D(0)


@dataclass(frozen=True)
class GLJournal:
    lines: list[JournalLine] = field(default_factory=list)

    @property
    def total_debit(self) -> Money:
        return sum((line.debit for line in self.lines), D(0))

    @property
    def total_credit(self) -> Money:
        return sum((line.credit for line in self.lines), D(0))

    @property
    def balanced(self) -> bool:
        return self.total_debit == self.total_credit


def gl_journal(payslips: list[dict[str, Any]]) -> GLJournal:
    """Double-entry payroll journal. Debits = employer cost (gross + employer
    PF/ESI); credits = net payable + statutory liabilities. Always balances."""
    gross = sum((Decimal(str(p["gross"])) for p in payslips), D(0))
    net = sum((Decimal(str(p["net_pay"])) for p in payslips), D(0))
    s = statutory_totals(payslips)

    lines = [
        JournalLine("Salaries & Wages (expense)", debit=gross),
        JournalLine("Employer PF contribution (expense)", debit=s.pf_employer),
    ]
    if s.esi_employer > 0:
        lines.append(JournalLine("Employer ESI contribution (expense)", debit=s.esi_employer))

    lines.append(JournalLine("Net pay payable (employees)", credit=net))
    if s.pf_total > 0:
        lines.append(JournalLine("PF payable", credit=s.pf_total))
    if s.esi_total > 0:
        lines.append(JournalLine("ESI payable", credit=s.esi_total))
    if s.pt > 0:
        lines.append(JournalLine("Professional tax payable", credit=s.pt))
    if s.tds > 0:
        lines.append(JournalLine("TDS payable", credit=s.tds))

    return GLJournal(lines)
