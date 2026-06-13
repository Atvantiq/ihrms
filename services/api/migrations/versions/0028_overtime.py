"""Overtime requests + payroll OT pay (M2)

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-13

Employees log overtime hours for a day; a manager/HR approves; approved OT is
paid in the next payroll run (hours x multiplier x hourly rate). Tenant-scoped
with RLS.
"""

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.overtime (
            id              uuid primary key default gen_random_uuid(),
            tenant_id       text not null default 'atvantiq',
            employee_id     bigint not null,
            ot_date         date not null,
            hours           numeric(4,1) not null check (hours > 0 and hours <= 24),
            rate_multiplier numeric(3,1) not null default 2.0
                            check (rate_multiplier >= 1),
            reason          text not null,
            status          text not null default 'pending'
                            check (status in ('pending','approved','rejected','paid')),
            run_id          uuid,
            decided_by      bigint,
            decided_at      timestamptz,
            created_at      timestamptz not null default now(),
            unique (tenant_id, employee_id, ot_date)
        )
    """)
    op.execute("create index ix_overtime_emp on ihrms.overtime (tenant_id, employee_id, status)")
    op.execute("alter table ihrms.overtime enable row level security")
    op.execute("alter table ihrms.overtime force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.overtime
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.overtime")
