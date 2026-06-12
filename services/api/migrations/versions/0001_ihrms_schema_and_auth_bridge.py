"""ihrms schema, auth bridge table, canonical employee view

Revision ID: 0001
Revises:
Create Date: 2026-06-12

Creates ONLY objects in the `ihrms` schema. Touches nothing in `public`
(ONAQT production tables) — see blueprint doc 24 for the contract.
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Bridge: Supabase auth user <-> ONAQT employee + iHRMS roles.
    # Soft references only (no FK into public/auth) so neither system
    # can ever block the other.
    op.execute("""
        create table ihrms.user_account (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            auth_user_id  uuid not null unique,          -- auth.users.id (soft ref)
            employee_id   bigint not null unique,        -- public.employees.employee_id (soft ref)
            roles         text[] not null default '{employee}',
            persona       text not null default 'employee',
            is_active     boolean not null default true,
            created_at    timestamptz not null default now(),
            updated_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_user_account_tenant on ihrms.user_account (tenant_id)")

    # RLS on from day one for all ihrms tables (service role bypasses;
    # policies tighten as personas land).
    op.execute("alter table ihrms.user_account enable row level security")

    # Canonical employee read model over the shared ONAQT tables.
    # App code reads THIS, never public.* directly.
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
    """)


def downgrade() -> None:
    op.execute("drop view if exists ihrms.v_employee")
    op.execute("drop table if exists ihrms.user_account")
