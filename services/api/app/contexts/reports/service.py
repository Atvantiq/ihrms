"""Reporting helpers — CSV serialization + simple analytics (pure, tested)."""

import csv
import io
from decimal import Decimal
from typing import Any


def to_csv(columns: list[str], rows: list[dict[str, Any]]) -> str:
    """Serialize report rows to CSV with a header from `columns`."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for r in rows:
        writer.writerow([_cell(r.get(c)) for c in columns])
    return buf.getvalue()


def _cell(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def attrition_rate(exits: int, avg_headcount: int) -> Decimal:
    """Annualised-period attrition % = exits / average headcount × 100."""
    if avg_headcount <= 0:
        return Decimal(0)
    return (Decimal(exits) / Decimal(avg_headcount) * Decimal(100)).quantize(Decimal("0.1"))
