"""Pure onboarding helpers — checklist progress."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Progress:
    done: int
    total: int
    pct: int  # 0-100, integer percent (100 only when all done)


def progress(statuses: list[str]) -> Progress:
    """Summarise a checklist from its task statuses ('done' counts as complete)."""
    total = len(statuses)
    done = sum(1 for s in statuses if s == "done")
    pct = 0 if total == 0 else round(done * 100 / total)
    return Progress(done=done, total=total, pct=pct)
