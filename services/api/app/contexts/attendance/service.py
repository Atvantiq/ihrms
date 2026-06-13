"""Attendance derivation — pure, testable.

A day's effective status combines (in priority order): explicit mark
(present/absent/wfh) > approved leave > holiday > weekend > not-marked.
LOP (loss of pay) = absent days + past working days left unmarked.
"""

import calendar
from dataclasses import dataclass
from datetime import date

# effective per-day statuses
PRESENT = "present"
WFH = "wfh"
ABSENT = "absent"
LEAVE = "leave"
HOLIDAY = "holiday"
WEEKEND = "weekend"
NOT_MARKED = "not_marked"  # past working day with no mark → counts as LOP
UPCOMING = "upcoming"      # future working day, not yet actionable


@dataclass(frozen=True)
class DayStatus:
    day: date
    status: str


@dataclass(frozen=True)
class MonthSummary:
    days: list[DayStatus]
    present: int
    wfh: int
    leave: int
    holiday: int
    weekend: int
    absent: int
    not_marked: int
    upcoming: int

    @property
    def lop(self) -> int:
        """Days that reduce pay: explicit absences + unmarked past working days."""
        return self.absent + self.not_marked

    @property
    def payable(self) -> int:
        return self.present + self.wfh + self.leave + self.holiday + self.weekend


def derive_month(
    year: int,
    month: int,
    today: date,
    marks: dict[date, str],
    leave_dates: set[date],
    holiday_dates: set[date],
) -> MonthSummary:
    days: list[DayStatus] = []
    counts = dict.fromkeys(
        [PRESENT, WFH, ABSENT, LEAVE, HOLIDAY, WEEKEND, NOT_MARKED, UPCOMING], 0
    )
    n_days = calendar.monthrange(year, month)[1]
    for d in range(1, n_days + 1):
        cur = date(year, month, d)
        if cur in marks:
            status = marks[cur]  # present | absent | wfh
        elif cur in leave_dates:
            status = LEAVE
        elif cur in holiday_dates:
            status = HOLIDAY
        elif cur.weekday() >= 5:
            status = WEEKEND
        elif cur > today:
            status = UPCOMING
        else:
            status = NOT_MARKED
        days.append(DayStatus(cur, status))
        counts[status] += 1
    return MonthSummary(
        days=days,
        present=counts[PRESENT],
        wfh=counts[WFH],
        leave=counts[LEAVE],
        holiday=counts[HOLIDAY],
        weekend=counts[WEEKEND],
        absent=counts[ABSENT],
        not_marked=counts[NOT_MARKED],
        upcoming=counts[UPCOMING],
    )
