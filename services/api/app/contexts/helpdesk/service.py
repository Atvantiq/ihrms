"""Ticket lifecycle rules (pure)."""

CATEGORIES = ["payroll", "leave", "it", "facilities", "hr_policy", "other"]
PRIORITIES = ["low", "medium", "high"]
STATUSES = ["open", "in_progress", "resolved", "closed"]

# Allowed status transitions.
_NEXT: dict[str, set[str]] = {
    "open": {"in_progress", "resolved", "closed"},
    "in_progress": {"resolved", "closed"},
    "resolved": {"closed", "in_progress"},  # reopen if needed
    "closed": set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in _NEXT.get(current, set())
