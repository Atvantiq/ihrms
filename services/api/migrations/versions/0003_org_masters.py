"""Org masters + raw-value mapping + canonical employee view

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-12

job_details department/division/branch/designation are uncontrolled free
text in ONAQT ('TELECOM'/'Telecome'/'TELECOME', 'it'/'IT'...). This adds
governed masters in the ihrms schema WITHOUT touching ONAQT rows:

- ihrms.org_masters     — canonical names per kind
- ihrms.org_value_map   — raw text -> master (translation layer for reads)
- seeds: distinct raw values grouped case-insensitively; most frequent
  casing wins as the master name; every raw spelling gets a mapping row.
  Cross-casing leftovers ('Telecome' vs 'TELECOM') are merged by HR in
  the review screen.
- ihrms.v_employee v2   — adds canonical department/division/branch/
  designation columns (coalesce to raw when unmapped).

ONAQT keeps reading its own raw values; iHRMS reads canonical.
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_KINDS_SRC = """
    select 'department' as kind, department as val from public.job_details
    union all select 'division', division from public.job_details
    union all select 'branch', branch from public.job_details
    union all select 'designation', designation from public.job_details
"""


def upgrade() -> None:
    op.execute("""
        create table ihrms.org_masters (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            kind        text not null check
                        (kind in ('department','division','branch','designation')),
            name        text not null,
            is_active   boolean not null default true,
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now()
        )
    """)
    op.execute("""
        create unique index ux_org_masters_kind_name
        on ihrms.org_masters (tenant_id, kind, lower(name))
        where is_active
    """)
    op.execute("alter table ihrms.org_masters enable row level security")

    op.execute("""
        create table ihrms.org_value_map (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            kind        text not null,
            raw_value   text not null,
            master_id   uuid not null references ihrms.org_masters(id),
            created_at  timestamptz not null default now(),
            unique (tenant_id, kind, raw_value)
        )
    """)
    op.execute("alter table ihrms.org_value_map enable row level security")

    # Seed masters: group raw values case-insensitively, keep the most
    # frequent spelling as the canonical name.
    op.execute(f"""
        insert into ihrms.org_masters (kind, name)
        select kind, mode() within group (order by trim(val)) as name
        from ({_KINDS_SRC}) t
        where val is not null and trim(val) <> ''
        group by kind, lower(trim(val))
    """)

    # Seed mappings: every distinct raw spelling points at its master.
    op.execute(f"""
        insert into ihrms.org_value_map (kind, raw_value, master_id)
        select distinct t.kind, t.val, m.id
        from ({_KINDS_SRC}) t
        join ihrms.org_masters m
          on m.kind = t.kind and lower(m.name) = lower(trim(t.val))
        where t.val is not null and trim(t.val) <> ''
    """)

    # v_employee v2: canonical org columns via the mapping.
    op.execute("drop view ihrms.v_employee")
    op.execute("""
        create view ihrms.v_employee as
        select
            e.employee_id,
            e.employee_code,
            e.email,
            e.first_name,
            e.middle_name,
            e.last_name,
            e.short_name,
            e.phone,
            e.date_of_birth,
            e.gender,
            e.is_active = 1                         as is_active,
            jd.designation,
            jd.department,
            jd.division,
            jd.branch,
            coalesce(md.name, jd.designation)       as designation_c,
            coalesce(mdep.name, jd.department)      as department_c,
            coalesce(mdiv.name, jd.division)        as division_c,
            coalesce(mbr.name, jd.branch)           as branch_c,
            jd.circle_id,
            jd.reporting_manager                    as reporting_manager_id,
            jd.date_of_joining,
            jd.date_of_leaving,
            ed.fathers_name,
            ed.mothers_name,
            ed.marital_status,
            ed.spouse_name,
            ed.alternate_phone,
            ed.pan_no,
            ed.adhar_no                             as aadhaar_no,
            ua.auth_user_id,
            ua.roles,
            ua.persona
        from public.employees e
        left join public.job_details jd
               on jd.employee_id = e.employee_id and jd.is_active = 1
        left join public.employee_details ed
               on ed.employee_id = e.employee_id
        left join ihrms.user_account ua
               on ua.employee_id = e.employee_id
        left join ihrms.org_value_map vd
               on vd.kind = 'designation' and vd.raw_value = jd.designation
        left join ihrms.org_masters md on md.id = vd.master_id
        left join ihrms.org_value_map vdep
               on vdep.kind = 'department' and vdep.raw_value = jd.department
        left join ihrms.org_masters mdep on mdep.id = vdep.master_id
        left join ihrms.org_value_map vdiv
               on vdiv.kind = 'division' and vdiv.raw_value = jd.division
        left join ihrms.org_masters mdiv on mdiv.id = vdiv.master_id
        left join ihrms.org_value_map vbr
               on vbr.kind = 'branch' and vbr.raw_value = jd.branch
        left join ihrms.org_masters mbr on mbr.id = vbr.master_id
    """)


def downgrade() -> None:
    op.execute("drop view if exists ihrms.v_employee")
    op.execute("drop table if exists ihrms.org_value_map")
    op.execute("drop table if exists ihrms.org_masters")
    # restore v1 view
    op.execute("""
        create view ihrms.v_employee as
        select
            e.employee_id, e.employee_code, e.email, e.first_name,
            e.middle_name, e.last_name, e.short_name, e.phone,
            e.date_of_birth, e.gender, e.is_active = 1 as is_active,
            jd.designation, jd.department, jd.division, jd.branch,
            jd.circle_id, jd.reporting_manager as reporting_manager_id,
            jd.date_of_joining, jd.date_of_leaving,
            ed.fathers_name, ed.mothers_name, ed.marital_status,
            ed.spouse_name, ed.alternate_phone, ed.pan_no,
            ed.adhar_no as aadhaar_no,
            ua.auth_user_id, ua.roles, ua.persona
        from public.employees e
        left join public.job_details jd
               on jd.employee_id = e.employee_id and jd.is_active = 1
        left join public.employee_details ed
               on ed.employee_id = e.employee_id
        left join ihrms.user_account ua
               on ua.employee_id = e.employee_id
    """)
