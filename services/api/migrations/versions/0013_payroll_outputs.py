"""Payroll outputs: employee bank + run 'paid' state

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-13

Adds employee bank details (for the disbursement/bank file) and a 'paid'
state to the payroll run (draft → finalized → paid). ihrms-schema only.
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.employee_bank (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            employee_id    bigint not null,
            account_number text not null,
            ifsc           text not null,
            bank_name      text,
            is_active      boolean not null default true,
            created_at     timestamptz not null default now(),
            updated_at     timestamptz not null default now()
        )
    """)
    op.execute(
        "create unique index ux_emp_bank_active on ihrms.employee_bank "
        "(tenant_id, employee_id) where is_active"
    )
    op.execute("alter table ihrms.employee_bank enable row level security")
    op.execute("alter table ihrms.employee_bank force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.employee_bank
           using (tenant_id = current_setting('app.tenant_id', true))
           with check (tenant_id = current_setting('app.tenant_id', true))"""
    )

    # allow the 'paid' state on payroll runs
    op.execute("alter table ihrms.payroll_run drop constraint payroll_run_status_check")
    op.execute(
        "alter table ihrms.payroll_run add constraint payroll_run_status_check "
        "check (status in ('draft', 'finalized', 'paid'))"
    )
    op.execute("alter table ihrms.payroll_run add column paid_at timestamptz")


def downgrade() -> None:
    op.execute("alter table ihrms.payroll_run drop column if exists paid_at")
    op.execute("alter table ihrms.payroll_run drop constraint payroll_run_status_check")
    op.execute(
        "alter table ihrms.payroll_run add constraint payroll_run_status_check "
        "check (status in ('draft', 'finalized'))"
    )
    op.execute("drop table if exists ihrms.employee_bank")
