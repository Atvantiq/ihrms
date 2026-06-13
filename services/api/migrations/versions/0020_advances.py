"""Advances & loans with payroll/F&F recovery (M3 backlog)

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-13

Salary advances and loans issued to employees, recovered as EMIs during the
monthly payroll run and settled in full at exit (F&F). Each recovery is logged
so the outstanding balance is always reconstructable. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

_RLS = ["advance", "advance_recovery"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.advance (
            id               uuid primary key default gen_random_uuid(),
            tenant_id        text not null default 'atvantiq',
            employee_id      bigint not null,
            kind             text not null default 'advance'
                             check (kind in ('advance','loan')),
            principal_amount numeric(12,2) not null check (principal_amount > 0),
            emi_amount       numeric(12,2) not null check (emi_amount > 0),
            outstanding      numeric(12,2) not null,
            reason           text,
            status           text not null default 'active'
                             check (status in ('active','closed','cancelled')),
            disbursed_on     date not null default current_date,
            created_by       bigint,
            created_at       timestamptz not null default now(),
            updated_at       timestamptz not null default now()
        )
    """)
    op.execute("create index ix_advance_emp on ihrms.advance (tenant_id, employee_id, status)")

    op.execute("""
        create table ihrms.advance_recovery (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            advance_id    uuid not null references ihrms.advance(id) on delete cascade,
            amount        numeric(12,2) not null,
            source        text not null default 'payroll'
                          check (source in ('payroll','fnf','manual')),
            run_id        uuid,
            recovered_on  date not null default current_date,
            created_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_recovery_advance on ihrms.advance_recovery (tenant_id, advance_id)")
    # at most one payroll recovery per advance per run (idempotent monthly run)
    op.execute(
        "create unique index ux_recovery_run on ihrms.advance_recovery "
        "(advance_id, run_id) where run_id is not null"
    )

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.advance_recovery")
    op.execute("drop table if exists ihrms.advance")
