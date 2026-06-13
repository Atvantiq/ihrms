"""Exit & Full-and-Final: exit cases, clearance, F&F settlement

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-13

Milestone 6 (capstone). A resignation creates an exit case + clearance
checklist; F&F is computed (gratuity/leave-encashment/notice-recovery),
approved, and paid — at which point access is revoked (employee +
job_details deactivated in the shared master). Tenant-scoped + RLS.
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

_RLS = ["exit_case", "clearance_item", "fnf_settlement"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.exit_case (
            id                   uuid primary key default gen_random_uuid(),
            tenant_id            text not null default 'atvantiq',
            employee_id          bigint not null,
            resignation_date     date not null,
            last_working_day     date not null,
            reason               text,
            notice_required_days int not null default 60,
            status               text not null default 'initiated'
                                 check (status in ('initiated','clearance','fnf_computed',
                                                   'approved','paid')),
            created_by           bigint,
            created_at           timestamptz not null default now(),
            updated_at           timestamptz not null default now()
        )
    """)
    op.execute(
        "create unique index ux_exit_active on ihrms.exit_case (tenant_id, employee_id) "
        "where status <> 'paid'"
    )

    op.execute("""
        create table ihrms.clearance_item (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            exit_case_id  uuid not null references ihrms.exit_case(id) on delete cascade,
            item          text not null,
            status        text not null default 'pending'
                          check (status in ('pending','cleared')),
            note          text,
            updated_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_clearance_case on ihrms.clearance_item (exit_case_id)")

    op.execute("""
        create table ihrms.fnf_settlement (
            id               uuid primary key default gen_random_uuid(),
            tenant_id        text not null default 'atvantiq',
            exit_case_id     uuid not null references ihrms.exit_case(id) on delete cascade,
            pending_salary   numeric(12,2) not null default 0,
            gratuity         numeric(12,2) not null default 0,
            leave_encashment numeric(12,2) not null default 0,
            notice_recovery  numeric(12,2) not null default 0,
            other_recoveries numeric(12,2) not null default 0,
            net_settlement   numeric(12,2) not null default 0,
            status           text not null default 'computed'
                             check (status in ('computed','approved','paid')),
            approved_by      bigint,
            created_at       timestamptz not null default now(),
            updated_at       timestamptz not null default now(),
            unique (tenant_id, exit_case_id)
        )
    """)

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.fnf_settlement")
    op.execute("drop table if exists ihrms.clearance_item")
    op.execute("drop table if exists ihrms.exit_case")
