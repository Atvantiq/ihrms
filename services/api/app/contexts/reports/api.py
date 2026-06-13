"""Reports & analytics (HR) — prebuilt cross-module reports + insights + CSV."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import ROLE_HR_ADMIN, Principal, require_roles
from app.contexts.reports.service import to_csv
from app.core.db import get_session

router = APIRouter(prefix="/reports", tags=["reports"])
HR = require_roles(ROLE_HR_ADMIN)


# Each report: human name, description, ordered columns, and a read-only SQL.
REPORTS: dict[str, dict[str, Any]] = {
    "headcount_by_department": {
        "name": "Headcount by department",
        "description": "Active employees grouped by canonical department.",
        "columns": ["department", "headcount"],
        "sql": """select coalesce(department_c,'(unassigned)') as department,
                         count(*) as headcount
                  from ihrms.v_employee where is_active
                  group by department_c order by headcount desc""",
    },
    "new_hires_90d": {
        "name": "New hires (90 days)",
        "description": "Employees who joined in the last 90 days.",
        "columns": ["employee_code", "name", "designation", "department", "date_of_joining"],
        "sql": """select employee_code,
                         trim(concat(first_name,' ',coalesce(last_name,''))) as name,
                         designation_c as designation, department_c as department,
                         date_of_joining
                  from ihrms.v_employee
                  where date_of_joining >= current_date - 90
                  order by date_of_joining desc""",
    },
    "exits": {
        "name": "Exits / attrition",
        "description": "Completed (paid) exits with last working day.",
        "columns": ["name", "last_working_day", "reason", "net_settlement"],
        "sql": """select trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as name,
                         c.last_working_day, c.reason, f.net_settlement
                  from ihrms.exit_case c
                  left join public.employees e on e.employee_id = c.employee_id
                  left join ihrms.fnf_settlement f on f.exit_case_id = c.id
                  where c.status = 'paid' order by c.last_working_day desc""",
    },
    "leave_liability": {
        "name": "Leave liability",
        "description": "Encashable leave balance per employee (current year).",
        "columns": ["name", "leave_code", "available_days"],
        "sql": """select trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as name,
                         lt.code as leave_code,
                         (b.accrued + b.carried_forward - b.used) as available_days
                  from ihrms.leave_balance b
                  join ihrms.leave_type lt on lt.id = b.leave_type_id
                  left join public.employees e on e.employee_id = b.employee_id
                  where b.period_year = extract(year from current_date)::int
                    and (b.accrued + b.carried_forward - b.used) > 0
                  order by available_days desc""",
    },
    "payroll_register_latest": {
        "name": "Payroll register (latest run)",
        "description": "Per-employee gross/deductions/net for the most recent run.",
        "columns": ["name", "gross", "total_deductions", "net_pay"],
        "sql": """select trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as name,
                         p.gross, p.total_deductions, p.net_pay
                  from ihrms.payslip p
                  join ihrms.payroll_run r on r.id = p.run_id
                  left join public.employees e on e.employee_id = p.employee_id
                  where r.id = (select id from ihrms.payroll_run
                                order by period_year desc, period_month desc limit 1)
                  order by p.net_pay desc""",
    },
    "recruitment_funnel": {
        "name": "Recruitment funnel",
        "description": "Candidates grouped by pipeline stage.",
        "columns": ["stage", "candidates"],
        "sql": """select stage, count(*) as candidates from ihrms.candidate
                  group by stage order by candidates desc""",
    },
    "rating_distribution": {
        "name": "Performance rating distribution",
        "description": "Published final ratings across review cycles.",
        "columns": ["final_rating", "employees"],
        "sql": """select final_rating, count(*) as employees from ihrms.review
                  where status = 'published' and final_rating is not null
                  group by final_rating order by final_rating desc""",
    },
}


class ReportMeta(BaseModel):
    id: str
    name: str
    description: str
    columns: list[str]


class ReportData(BaseModel):
    id: str
    name: str
    columns: list[str]
    rows: list[dict[str, Any]]


@router.get("", response_model=list[ReportMeta])
async def list_reports(
    principal: Annotated[Principal, HR],
) -> list[ReportMeta]:
    return [
        ReportMeta(id=rid, name=r["name"], description=r["description"], columns=r["columns"])
        for rid, r in REPORTS.items()
    ]


async def _run(
    session: AsyncSession, report_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report = REPORTS.get(report_id)
    if report is None:
        raise HTTPException(404, "Report not found")
    result = await session.execute(text(report["sql"]))
    rows = [dict(r) for r in result.mappings().all()]
    return report, rows


@router.get("/insights")
async def insights(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> dict[str, Any]:
    headcount = (
        await session.execute(text("select count(*) from ihrms.v_employee where is_active"))
    ).scalar_one()
    exits = (
        await session.execute(
            text("select count(*) from ihrms.exit_case where status='paid'")
        )
    ).scalar_one()
    latest_net = (
        await session.execute(
            text("""select total_net from ihrms.payroll_run
                    order by period_year desc, period_month desc limit 1""")
        )
    ).scalar()
    avg_tenure = (
        await session.execute(
            text("""select round(avg(extract(epoch from
                       age(current_date, date_of_joining)) / 2629800))
                    from ihrms.v_employee
                    where is_active and date_of_joining is not null""")
        )
    ).scalar()
    open_reqs = (
        await session.execute(
            text("select count(*) from ihrms.requisition where status='open'")
        )
    ).scalar_one()
    return {
        "headcount": int(headcount),
        "exits_total": int(exits),
        "latest_monthly_net": str(latest_net) if latest_net is not None else None,
        "avg_tenure_months": int(avg_tenure) if avg_tenure is not None else None,
        "open_requisitions": int(open_reqs),
    }


@router.get("/{report_id}", response_model=ReportData)
async def run_report(
    report_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ReportData:
    report, rows = await _run(session, report_id)
    return ReportData(id=report_id, name=report["name"], columns=report["columns"], rows=rows)


@router.get("/{report_id}/csv")
async def report_csv(
    report_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Response:
    report, rows = await _run(session, report_id)
    csv_text = to_csv(report["columns"], rows)
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report_id}.csv"'},
    )
