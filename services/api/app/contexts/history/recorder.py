"""Records effective-dated changes to the employee_history log.

Called from the write paths (employee update, salary structure) — it only
persists fields that actually changed, so the timeline stays meaningful.
Inserts only; no commit (the caller owns the transaction).
"""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _norm(v: Any) -> str | None:
    if v is None:
        return None
    return str(v)


async def record_changes(
    session: AsyncSession,
    *,
    employee_id: int,
    category: str,
    changes: list[tuple[str, Any, Any]],
    changed_by: int | None,
    effective_date: date | None = None,
    note: str | None = None,
) -> None:
    """`changes` is (field, old, new) triples; rows are written only where the
    normalised old and new differ."""
    eff = effective_date or date.today()
    for field, old, new in changes:
        old_s, new_s = _norm(old), _norm(new)
        if old_s == new_s:
            continue
        await session.execute(
            text("""insert into ihrms.employee_history
                    (employee_id, category, field, old_value, new_value,
                     effective_date, changed_by, note)
                    values (:e, :cat, :f, :old, :new, :eff, :by, :note)"""),
            {"e": employee_id, "cat": category, "f": field, "old": old_s, "new": new_s,
             "eff": eff, "by": changed_by, "note": note},
        )
