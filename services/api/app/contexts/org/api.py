"""Org masters — review & merge the free-text values from job_details.

All writes are ihrms-schema only. ONAQT's raw text in public.job_details
is never rewritten; the mapping table translates raw -> canonical for
iHRMS reads, and merges just re-point mappings.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import ROLE_HR_ADMIN, Principal, require_roles
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/org", tags=["org"])

Kind = Literal["department", "division", "branch", "designation"]


class MasterOut(BaseModel):
    id: str
    kind: Kind
    name: str
    raw_values: list[str]
    employee_count: int


class MasterCreate(BaseModel):
    kind: Kind
    name: str = Field(min_length=1, max_length=120)


class MasterRename(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class MasterMerge(BaseModel):
    into_master_id: str


_LIST_SQL = text("""
    with usage as (
        select v.master_id, v.raw_value,
               (select count(*) from public.job_details jd
                where jd.is_active = 1
                  and case v.kind
                        when 'department'  then jd.department
                        when 'division'    then jd.division
                        when 'branch'      then jd.branch
                        when 'designation' then jd.designation
                      end = v.raw_value) as cnt
        from ihrms.org_value_map v
    )
    select m.id::text, m.kind, m.name,
           coalesce(array_agg(u.raw_value order by u.raw_value)
                    filter (where u.raw_value is not null), '{}') as raw_values,
           coalesce(sum(u.cnt), 0)::int as employee_count
    from ihrms.org_masters m
    left join ihrms.org_value_map vm on vm.master_id = m.id
    left join usage u on u.master_id = m.id and u.raw_value = vm.raw_value
    where m.is_active and (:kind = '' or m.kind = :kind)
    group by m.id, m.kind, m.name
    order by m.kind, lower(m.name)
""")


@router.get("/masters", response_model=list[MasterOut])
async def list_masters(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
    kind: str = "",
) -> list[MasterOut]:
    rows = (await session.execute(_LIST_SQL, {"kind": kind})).mappings().all()
    return [MasterOut(**dict(r)) for r in rows]


@router.post("/masters", response_model=MasterOut, status_code=201)
async def create_master(
    payload: MasterCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> MasterOut:
    dup = (
        await session.execute(
            text("""select 1 from ihrms.org_masters
                    where kind = :kind and lower(name) = lower(:name) and is_active"""),
            {"kind": payload.kind, "name": payload.name.strip()},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, f"A {payload.kind} with this name already exists")
    row = (
        await session.execute(
            text("""insert into ihrms.org_masters (kind, name)
                    values (:kind, :name) returning id::text, kind, name"""),
            {"kind": payload.kind, "name": payload.name.strip()},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "org_master.create", "org_master", row["id"],
        summary=f"Created {payload.kind} '{payload.name.strip()}'",
    )
    await session.commit()
    return MasterOut(**dict(row), raw_values=[], employee_count=0)


@router.patch("/masters/{master_id}", response_model=MasterOut)
async def rename_master(
    master_id: str,
    payload: MasterRename,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> MasterOut:
    row = (
        await session.execute(
            text("""update ihrms.org_masters set name = :name, updated_at = now()
                    where id = :id and is_active returning id::text, kind"""),
            {"id": master_id, "name": payload.name.strip()},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Master not found")
    await record_audit(
        session, principal, "org_master.rename", "org_master", master_id,
        summary=f"Renamed to '{payload.name.strip()}'",
    )
    await session.commit()
    masters = await list_masters(session, principal, kind=row["kind"])
    return next(m for m in masters if m.id == master_id)


@router.post("/masters/{master_id}/merge", response_model=MasterOut)
async def merge_master(
    master_id: str,
    payload: MasterMerge,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> MasterOut:
    """Merge `master_id` INTO `into_master_id`: re-point all raw-value
    mappings, deactivate the source. ONAQT rows are untouched."""
    if master_id == payload.into_master_id:
        raise HTTPException(409, "Cannot merge a master into itself")
    pair = (
        await session.execute(
            text("""select
                (select kind from ihrms.org_masters where id = :src and is_active) as src_kind,
                (select kind from ihrms.org_masters where id = :dst and is_active) as dst_kind
            """),
            {"src": master_id, "dst": payload.into_master_id},
        )
    ).mappings().one()
    if pair["src_kind"] is None or pair["dst_kind"] is None:
        raise HTTPException(404, "Master not found")
    if pair["src_kind"] != pair["dst_kind"]:
        raise HTTPException(409, "Masters must be of the same kind")

    await session.execute(
        text("update ihrms.org_value_map set master_id = :dst where master_id = :src"),
        {"src": master_id, "dst": payload.into_master_id},
    )
    await session.execute(
        text("""update ihrms.org_masters set is_active = false, updated_at = now()
                where id = :src"""),
        {"src": master_id},
    )
    await record_audit(
        session, principal, "org_master.merge", "org_master", master_id,
        summary=f"Merged into {payload.into_master_id}",
        changes={"into_master_id": payload.into_master_id},
    )
    await session.commit()
    masters = await list_masters(session, principal, kind=pair["dst_kind"])
    return next(m for m in masters if m.id == payload.into_master_id)
