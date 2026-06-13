"""Shifts & rostering (M2)

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-13

Shift definitions (timings + break) and effective-dated per-employee shift
assignments. Drives the roster and gives attendance a reference for expected
hours. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

_RLS = ["shift", "shift_assignment"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.shift (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            code          text not null,
            name          text not null,
            start_time    time not null,
            end_time      time not null,
            break_minutes int not null default 0 check (break_minutes >= 0),
            is_night      boolean not null default false,
            is_active     boolean not null default true,
            created_at    timestamptz not null default now(),
            updated_at    timestamptz not null default now(),
            unique (tenant_id, code)
        )
    """)

    op.execute("""
        create table ihrms.shift_assignment (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            employee_id    bigint not null,
            shift_id       uuid not null references ihrms.shift(id),
            effective_from date not null default current_date,
            effective_to   date,
            created_by     bigint,
            created_at     timestamptz not null default now()
        )
    """)
    op.execute(
        "create index ix_shiftassign_emp on ihrms.shift_assignment "
        "(tenant_id, employee_id, effective_from desc)"
    )
    # one open (no end date) assignment per employee at a time
    op.execute(
        "create unique index ux_shiftassign_open on ihrms.shift_assignment "
        "(employee_id) where effective_to is null"
    )

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )

    # a sensible default general shift
    op.execute("""
        insert into ihrms.shift (code, name, start_time, end_time, break_minutes)
        values ('GEN', 'General (9:30-18:30)', '09:30', '18:30', 60)
    """)


def downgrade() -> None:
    op.execute("drop table if exists ihrms.shift_assignment")
    op.execute("drop table if exists ihrms.shift")
