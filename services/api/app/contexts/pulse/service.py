"""Pulse — the ranked decision inbox engine.

Pulse turns the data the rest of the system already holds into a short,
ranked list of *decisions waiting on you*: leave/timesheet/increment approvals,
probation confirmations, exit settlements, payroll readiness. It is rules-based
and deterministic (no LLM) — every card is traceable to a real row.

This module is the pure ranking core (no DB); the SQL gathering lives in
`api.py`. Keeping the ordering here makes it unit-testable.
"""

from typing import Literal

from pydantic import BaseModel

Severity = Literal["high", "medium", "low"]

# Lower weight sorts first. High-urgency, money/compliance, and time-bound
# decisions float to the top of the inbox.
_SEVERITY_WEIGHT: dict[Severity, int] = {"high": 0, "medium": 1, "low": 2}


class Decision(BaseModel):
    """One actionable card in the Pulse inbox."""

    kind: str
    severity: Severity
    icon: str
    title: str
    detail: str
    action_label: str
    action_href: str
    count: int = 0


def rank_decisions(decisions: list[Decision]) -> list[Decision]:
    """Order by severity, then by how many items are stacked behind the card.

    Stable within a (severity, count) tier so the gather order is preserved
    for equally-urgent cards.
    """
    return sorted(
        decisions,
        key=lambda d: (_SEVERITY_WEIGHT[d.severity], -d.count),
    )


def severity_for_count(count: int, *, high_at: int, medium_at: int = 1) -> Severity:
    """Escalate a card's severity by backlog size (e.g. 1 pending = medium,
    10 pending = high). Below `medium_at` the caller should drop the card."""
    if count >= high_at:
        return "high"
    if count >= medium_at:
        return "medium"
    return "low"
