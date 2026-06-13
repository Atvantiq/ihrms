"""Salary arrears from back-dated structure changes (M3 backlog)

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-13

When a salary structure is made effective in a past month, the gross difference
for the already-paid months becomes an arrear, paid out in the next payroll run.
Tenant-scoped with RLS.
"""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.arrear (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            employee_id    bigint not null,
            amount         numeric(12,2) not null,
            months         int not null,
            reason         text,
            effective_from date not null,
            status         text not null default 'pending'
                           check (status in ('pending','paid','cancelled')),
            run_id         uuid,
            created_by     bigint,
            created_at     timestamptz not null default now()
        )
    """)
    op.execute("create index ix_arrear_emp on ihrms.arrear (tenant_id, employee_id, status)")
    op.execute("alter table ihrms.arrear enable row level security")
    op.execute("alter table ihrms.arrear force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.arrear
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.arrear")
