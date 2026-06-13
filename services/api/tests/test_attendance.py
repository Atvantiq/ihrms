"""Golden tests for attendance month derivation — pure, no DB."""

from datetime import date

from app.contexts.attendance.service import derive_month


def test_weekends_and_working_days_counted() -> None:
    # June 2026: 30 days. Today far in the future so no "upcoming".
    m = derive_month(2026, 6, date(2026, 7, 1), {}, set(), set())
    assert len(m.days) == 30
    # June 2026 has 8 weekend days (Sat/Sun)
    assert m.weekend == 8
    # all working days unmarked (no leave/holiday/marks)
    assert m.not_marked == 30 - 8
    assert m.lop == 22


def test_priority_mark_over_everything() -> None:
    d = date(2026, 6, 1)  # Monday
    m = derive_month(2026, 6, date(2026, 7, 1), {d: "present"}, {d}, {d})
    assert m.days[0].status == "present"  # explicit mark wins
    assert m.present == 1


def test_leave_and_holiday_and_present() -> None:
    today = date(2026, 6, 30)
    marks = {date(2026, 6, 1): "present", date(2026, 6, 2): "wfh"}
    leave = {date(2026, 6, 3), date(2026, 6, 4)}
    holiday = {date(2026, 6, 5)}
    m = derive_month(2026, 6, today, marks, leave, holiday)
    assert m.present == 1
    assert m.wfh == 1
    assert m.leave == 2
    assert m.holiday == 1
    # leave/holiday/present/wfh all payable; weekends payable too
    assert m.payable == m.present + m.wfh + m.leave + m.holiday + m.weekend


def test_future_days_are_upcoming_not_lop() -> None:
    # today mid-month: later working days are "upcoming", not LOP
    m = derive_month(2026, 6, date(2026, 6, 10), {}, set(), set())
    assert m.upcoming > 0
    # only past working days count as not_marked/LOP
    assert m.not_marked < 22


def test_absent_counts_as_lop() -> None:
    marks = {date(2026, 6, 1): "absent", date(2026, 6, 2): "present"}
    m = derive_month(2026, 6, date(2026, 6, 3), marks, set(), set())
    assert m.absent == 1
    assert m.lop >= 1
