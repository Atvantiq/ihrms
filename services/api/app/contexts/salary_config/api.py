"""Salary configuration API — component catalogue + structure preview.

HR manages the component catalogue (earnings/reimbursements/deductions/employer)
and previews how a CTC resolves into an itemised split. Tenant-scoped; audited.
"""

from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import ROLE_HR_ADMIN, Principal, require_roles
from app.contexts.payroll.statutory import compute_pf
from app.contexts.salary_config.service import Component, resolve_earnings
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.money import D, round_money

router = APIRouter(prefix="/salary-config", tags=["salary-config"])
HR = require_roles(ROLE_HR_ADMIN)


class ComponentOut(BaseModel):
    id: str
    code: str
    name: str
    component_type: str
    calc_type: str
    value: Decimal
    tax_treatment: str
    pf_wage: bool
    esi_wage: bool
    pt_wage: bool
    on_payslip: bool


class ComponentIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=80)
    component_type: Literal["earning", "reimbursement", "deduction", "employer"]
    calc_type: Literal["fixed", "pct_ctc", "pct_basic", "pct_gross", "balancing"]
    value: Decimal = Field(default=D(0), ge=0)
    tax_treatment: Literal["taxable", "partial", "exempt"] = "taxable"
    pf_wage: bool = False
    esi_wage: bool = False
    pt_wage: bool = False
    sort_order: int = 100


def _out(r: dict[str, Any]) -> ComponentOut:
    return ComponentOut(
        id=r["id"], code=r["code"], name=r["name"], component_type=r["component_type"],
        calc_type=r["calc_type"], value=r["value"], tax_treatment=r["tax_treatment"],
        pf_wage=r["pf_wage"], esi_wage=r["esi_wage"], pt_wage=r["pt_wage"],
        on_payslip=r["on_payslip"],
    )


@router.get("/components", response_model=list[ComponentOut])
async def list_components(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[ComponentOut]:
    rows = (
        await session.execute(
            text("""select id::text, code, name, component_type, calc_type, value,
                       tax_treatment, pf_wage, esi_wage, pt_wage, on_payslip
                    from ihrms.salary_component where is_active
                    order by sort_order, code""")
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


@router.post("/components", response_model=ComponentOut, status_code=201)
async def create_component(
    payload: ComponentIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ComponentOut:
    dup = (
        await session.execute(
            text("select 1 from ihrms.salary_component where code=:c"), {"c": payload.code}
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "Component code already exists")
    row = (
        await session.execute(
            text("""insert into ihrms.salary_component
                    (code, name, component_type, calc_type, value, tax_treatment,
                     pf_wage, esi_wage, pt_wage, sort_order)
                    values (:c, :n, :ct, :calc, :v, :tt, :pf, :esi, :pt, :so)
                    returning id::text, code, name, component_type, calc_type, value,
                              tax_treatment, pf_wage, esi_wage, pt_wage, on_payslip"""),
            {"c": payload.code, "n": payload.name, "ct": payload.component_type,
             "calc": payload.calc_type, "v": payload.value, "tt": payload.tax_treatment,
             "pf": payload.pf_wage, "esi": payload.esi_wage, "pt": payload.pt_wage,
             "so": payload.sort_order},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "salary_component.create", "salary_component", row["id"],
        summary=f"Added salary component {payload.code}",
    )
    out = _out(dict(row))
    await session.commit()
    return out


@router.delete("/components/{component_id}", status_code=204)
async def deactivate_component(
    component_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> None:
    await session.execute(
        text("update ihrms.salary_component set is_active=false where id=cast(:id as uuid)"),
        {"id": component_id},
    )
    await session.commit()


class PreviewLine(BaseModel):
    code: str
    name: str
    amount: Decimal


class StructurePreview(BaseModel):
    ctc_annual: Decimal
    monthly_ctc: Decimal
    lines: list[PreviewLine]
    gross_monthly: Decimal


@router.get("/preview", response_model=StructurePreview)
async def preview(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
    ctc_annual: Decimal,
) -> StructurePreview:
    """Resolve the active earning components for a given annual CTC."""
    if ctc_annual <= 0:
        raise HTTPException(422, "ctc_annual must be positive")
    rows = (
        await session.execute(
            text("""select code, name, component_type, calc_type, value
                    from ihrms.salary_component
                    where is_active and component_type in ('earning','reimbursement')
                    order by sort_order, code""")
        )
    ).mappings().all()
    comps = [
        Component(
            r["code"], r["name"], r["component_type"], r["calc_type"],
            Decimal(str(r["value"])),
        )
        for r in rows
    ]
    monthly_ctc = round_money(ctc_annual / D(12))
    # estimate the BASIC for employer PF, then resolve with that PF reserved from CTC
    basic_est = next(
        (round_money(monthly_ctc * c.value / D(100)) for c in comps if c.code == "BASIC"),
        round_money(monthly_ctc * D("0.40")),
    )
    employer_pf = compute_pf(basic_est).employer
    lines, gross = resolve_earnings(monthly_ctc, comps, employer_pf=employer_pf)
    return StructurePreview(
        ctc_annual=ctc_annual, monthly_ctc=monthly_ctc,
        lines=[PreviewLine(code=line.code, name=line.name, amount=line.amount) for line in lines],
        gross_monthly=gross,
    )
