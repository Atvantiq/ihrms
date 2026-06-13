"""Control plane (Track-B) — tenants, plans, billing, statutory master.

Platform-owner surface, gated to super_admin. Distinct from the tenant HR
app: it manages the SaaS itself (who the tenants are, what they pay, which
statutory pack is live).
"""

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import (
    ROLE_SUPER_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.db import get_session

router = APIRouter(prefix="/control-plane", tags=["control-plane"])
SUPER = require_roles(ROLE_SUPER_ADMIN)


# ---------------------------------------------------------------- plans

class PlanOut(BaseModel):
    code: str
    name: str
    price_per_employee: Decimal
    included_employees: int
    features: dict[str, Any]


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> list[PlanOut]:
    rows = (
        await session.execute(
            text("""select code, name, price_per_employee, included_employees, features
                    from ihrms.plan where is_active order by price_per_employee""")
        )
    ).mappings().all()
    return [PlanOut(**dict(r)) for r in rows]


# ---------------------------------------------------------------- tenants

class TenantOut(BaseModel):
    id: str
    name: str
    plan_code: str | None = None
    status: str
    region: str
    employee_count: int = 0
    mrr: Decimal = Decimal(0)


class TenantIn(BaseModel):
    id: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=120)
    plan_code: str
    region: str = "ap-south-1"


async def _tenant_employee_count(session: AsyncSession, tenant_id: str) -> int:
    """Active employees for a tenant. Data is single-tenant today, so only the
    configured tenant has employees; others are 0 until they onboard."""
    if tenant_id != get_settings().tenant_id:
        return 0
    return int(
        (await session.execute(text("select count(*) from ihrms.v_employee where is_active")))
        .scalar_one()
    )


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> list[TenantOut]:
    rows = (
        await session.execute(
            text("""select t.id, t.name, t.plan_code, t.status, t.region,
                       p.price_per_employee as rate
                    from ihrms.tenant t
                    left join ihrms.plan p on p.code = t.plan_code
                    order by t.created_at""")
        )
    ).mappings().all()
    out: list[TenantOut] = []
    for r in rows:
        count = await _tenant_employee_count(session, r["id"])
        rate = Decimal(str(r["rate"] or 0))
        out.append(TenantOut(
            id=r["id"], name=r["name"], plan_code=r["plan_code"], status=r["status"],
            region=r["region"], employee_count=count, mrr=rate * count,
        ))
    return out


@router.post("/tenants", response_model=TenantOut, status_code=201)
async def create_tenant(
    payload: TenantIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> TenantOut:
    dup = (
        await session.execute(text("select 1 from ihrms.tenant where id=:id"), {"id": payload.id})
    ).scalar()
    if dup:
        raise HTTPException(409, "Tenant id already exists")
    plan = (
        await session.execute(
            text("select 1 from ihrms.plan where code=:c and is_active"), {"c": payload.plan_code}
        )
    ).scalar()
    if plan is None:
        raise HTTPException(404, "Plan not found")
    await session.execute(
        text("""insert into ihrms.tenant (id, name, plan_code, status, region)
                values (:id, :n, :p, 'trial', :r)"""),
        {"id": payload.id, "n": payload.name, "p": payload.plan_code, "r": payload.region},
    )
    await record_audit(
        session, principal, "tenant.create", "tenant", payload.id,
        summary=f"Provisioned tenant {payload.name} on {payload.plan_code}",
    )
    await session.commit()
    return TenantOut(id=payload.id, name=payload.name, plan_code=payload.plan_code,
                     status="trial", region=payload.region)


class TenantStatus(BaseModel):
    status: str = Field(pattern=r"^(trial|active|suspended|churned)$")


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
async def set_status(
    tenant_id: str,
    payload: TenantStatus,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> TenantOut:
    row = (
        await session.execute(
            text("""update ihrms.tenant set status=:s, updated_at=now() where id=:id
                    returning id, name, plan_code, status, region"""),
            {"s": payload.status, "id": tenant_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Tenant not found")
    await record_audit(
        session, principal, "tenant.status", "tenant", tenant_id,
        summary=f"Tenant {tenant_id} -> {payload.status}",
    )
    await session.commit()
    return TenantOut(**dict(row))


# ---------------------------------------------------------------- billing

class InvoiceOut(BaseModel):
    id: str
    tenant_id: str
    period_year: int
    period_month: int
    employee_count: int
    rate: Decimal
    amount: Decimal
    status: str


class BillingRun(BaseModel):
    period_year: int = Field(ge=2020, le=2100)
    period_month: int = Field(ge=1, le=12)


@router.post("/billing/run", response_model=list[InvoiceOut])
async def run_billing(
    payload: BillingRun,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> list[InvoiceOut]:
    """Generate PEPM invoices for active tenants: employees × plan rate."""
    tenants = (
        await session.execute(
            text("""select t.id, p.price_per_employee as rate from ihrms.tenant t
                    join ihrms.plan p on p.code = t.plan_code
                    where t.status in ('active','trial')""")
        )
    ).mappings().all()
    out: list[InvoiceOut] = []
    for t in tenants:
        count = await _tenant_employee_count(session, t["id"])
        rate = Decimal(str(t["rate"]))
        amount = rate * count
        row = (
            await session.execute(
                text("""insert into ihrms.invoice
                        (tenant_id, period_year, period_month, employee_count, rate, amount)
                        values (:t, :y, :m, :c, :r, :a)
                        on conflict (tenant_id, period_year, period_month) do update set
                          employee_count=:c, rate=:r, amount=:a
                        returning id::text, tenant_id, period_year, period_month,
                                  employee_count, rate, amount, status"""),
                {"t": t["id"], "y": payload.period_year, "m": payload.period_month,
                 "c": count, "r": rate, "a": amount},
            )
        ).mappings().one()
        out.append(InvoiceOut(**dict(row)))
    period = f"{payload.period_year}-{payload.period_month}"
    await record_audit(
        session, principal, "billing.run", "invoice", period,
        summary=f"Billed {len(out)} tenant(s) for {payload.period_month}/{payload.period_year}",
    )
    await session.commit()
    return out


@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> list[InvoiceOut]:
    rows = (
        await session.execute(
            text("""select id::text, tenant_id, period_year, period_month,
                       employee_count, rate, amount, status from ihrms.invoice
                    order by period_year desc, period_month desc, tenant_id""")
        )
    ).mappings().all()
    return [InvoiceOut(**dict(r)) for r in rows]


# ---------------------------------------------------------------- statutory master

class PackOut(BaseModel):
    id: str
    name: str
    country: str
    effective_from: str
    rates: dict[str, Any]
    is_active: bool


@router.get("/statutory-packs", response_model=list[PackOut])
async def list_packs(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> list[PackOut]:
    rows = (
        await session.execute(
            text("""select id::text, name, country, effective_from::text, rates, is_active
                    from ihrms.statutory_pack order by effective_from desc""")
        )
    ).mappings().all()
    return [PackOut(**dict(r)) for r in rows]


# ---------------------------------------------------------------- platform KPIs

@router.get("/insights")
async def platform_insights(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> dict[str, Any]:
    tenants = (await session.execute(text("select count(*) from ihrms.tenant"))).scalar_one()
    active = (
        await session.execute(text("select count(*) from ihrms.tenant where status='active'"))
    ).scalar_one()
    # MRR = sum over active tenants of (rate × employee count)
    rows = (
        await session.execute(
            text("""select t.id, p.price_per_employee as rate from ihrms.tenant t
                    join ihrms.plan p on p.code=t.plan_code where t.status='active'""")
        )
    ).mappings().all()
    mrr = Decimal(0)
    total_emp = 0
    for r in rows:
        c = await _tenant_employee_count(session, r["id"])
        total_emp += c
        mrr += Decimal(str(r["rate"])) * c
    return {
        "tenants": int(tenants),
        "active_tenants": int(active),
        "billable_employees": total_emp,
        "mrr": str(mrr),
    }


# ---------------------------------------------------------------- announcements

class AnnouncementOut(BaseModel):
    id: str
    title: str
    body: str
    level: str
    created_at: str


class AnnouncementIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=2000)
    level: str = Field(default="info", pattern=r"^(info|success|warning)$")


@router.get("/announcements", response_model=list[AnnouncementOut])
async def list_announcements(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[AnnouncementOut]:
    """Active announcements — visible to every authenticated user."""
    rows = (
        await session.execute(
            text("""select id::text, title, body, level, created_at::text
                    from ihrms.announcement where is_active
                    order by created_at desc limit 10""")
        )
    ).mappings().all()
    return [AnnouncementOut(**dict(r)) for r in rows]


@router.post("/announcements", response_model=AnnouncementOut, status_code=201)
async def post_announcement(
    payload: AnnouncementIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> AnnouncementOut:
    row = (
        await session.execute(
            text("""insert into ihrms.announcement (title, body, level, created_by)
                    values (:t, :b, :l, :by)
                    returning id::text, title, body, level, created_at::text"""),
            {"t": payload.title.strip(), "b": payload.body.strip(), "l": payload.level,
             "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "announcement.post", "announcement", row["id"],
        summary=f"Posted: {payload.title.strip()}",
    )
    out = AnnouncementOut(**dict(row))
    await session.commit()
    return out


@router.delete("/announcements/{ann_id}", status_code=204)
async def retract_announcement(
    ann_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, SUPER],
) -> None:
    await session.execute(
        text("update ihrms.announcement set is_active=false where id=:id"),
        {"id": ann_id},
    )
    await session.commit()
