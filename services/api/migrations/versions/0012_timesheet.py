"""Timesheet: projects, entries, weekly submission

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-13

Employees log hours against projects per day; a week (Mon–Sun) is submitted
for manager/HR approval. Tenant-scoped + RLS like the other ihrms tables.
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_RLS = ["project", "timesheet_entry", "timesheet_week"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.project (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            code        text not null,
            name        text not null,
            client      text,
            is_active   boolean not null default true,
            created_at  timestamptz not null default now()
        )
    """)
    op.execute("create unique index ux_project_code on ihrms.project (tenant_id, code)")

    op.execute("""
        create table ihrms.timesheet_week (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            week_start  date not null,
            status      text not null default 'draft'
                        check (status in ('draft','submitted','approved','rejected')),
            total_hours numeric(6,2) not null default 0,
            approver_id bigint,
            decision_note text,
            decided_at  timestamptz,
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now(),
            unique (tenant_id, employee_id, week_start)
        )
    """)

    op.execute("""
        create table ihrms.timesheet_entry (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            work_date   date not null,
            project_id  uuid not null references ihrms.project(id),
            hours       numeric(4,2) not null check (hours >= 0 and hours <= 24),
            note        text,
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now(),
            unique (tenant_id, employee_id, work_date, project_id)
        )
    """)
    op.execute(
        "create index ix_ts_entry_emp on ihrms.timesheet_entry "
        "(tenant_id, employee_id, work_date)"
    )

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )

    op.execute("""
        insert into ihrms.project (code, name, client) values
          ('INTERNAL', 'Internal / Admin', null),
          ('ATV-CORE', 'Atvantiq Platform', 'Atvantiq'),
          ('ONAQT', 'ONAQT Field Ops', 'Atvantiq')
    """)


def downgrade() -> None:
    op.execute("drop table if exists ihrms.timesheet_entry")
    op.execute("drop table if exists ihrms.timesheet_week")
    op.execute("drop table if exists ihrms.project")
