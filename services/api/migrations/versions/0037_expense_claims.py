"""Expense claims / reimbursements (M3 / ESS)

Revision ID: 0037
Revises: 0036
Create Date: 2026-06-13

Employees file expense claims (travel, food, …) with a receipt reference;
Finance/HR approves; approved claims are reimbursed in the next payroll run.
Tenant-scoped with RLS.
"""

from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.expense_claim (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            category    text not null
                        check (category in ('travel','food','accommodation',
                                            'supplies','communication','other')),
            description text not null,
            claim_date  date not null,
            amount      numeric(12,2) not null check (amount > 0),
            receipt_ref text,
            status      text not null default 'pending'
                        check (status in ('pending','approved','rejected','paid')),
            decided_by  bigint,
            decided_at  timestamptz,
            run_id      uuid,
            created_at  timestamptz not null default now()
        )
    """)
    op.execute("create index ix_claim_emp on ihrms.expense_claim (tenant_id, employee_id, status)")
    op.execute("alter table ihrms.expense_claim enable row level security")
    op.execute("alter table ihrms.expense_claim force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.expense_claim
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.expense_claim")
