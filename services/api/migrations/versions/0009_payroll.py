"""Payroll: salary structures, runs, payslips

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-13

Tenant-scoped (RLS forced + policy, like the other ihrms tables). Money is
numeric(12,2). A run computes one payslip per active employee with a salary
structure; payslips store the earnings/deductions breakdown as jsonb plus
the headline gross/deductions/net for fast listing.
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_RLS_TABLES = ["salary_structure", "payroll_run", "payslip"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.salary_structure (
            id                 uuid primary key default gen_random_uuid(),
            tenant_id          text not null default 'atvantiq',
            employee_id        bigint not null,
            ctc_annual         numeric(12,2) not null,
            basic              numeric(12,2) not null,
            hra                numeric(12,2) not null,
            special_allowance  numeric(12,2) not null,
            effective_from     date not null,
            is_active          boolean not null default true,
            created_at         timestamptz not null default now(),
            updated_at         timestamptz not null default now()
        )
    """)
    op.execute(
        "create unique index ux_salary_active on ihrms.salary_structure "
        "(tenant_id, employee_id) where is_active"
    )

    op.execute("""
        create table ihrms.payroll_run (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            period_year   int not null,
            period_month  int not null check (period_month between 1 and 12),
            working_days  int not null default 30,
            status        text not null default 'draft'
                          check (status in ('draft', 'finalized')),
            employee_count int not null default 0,
            total_gross   numeric(14,2) not null default 0,
            total_net     numeric(14,2) not null default 0,
            created_by    bigint,
            created_at    timestamptz not null default now(),
            finalized_at  timestamptz,
            unique (tenant_id, period_year, period_month)
        )
    """)

    op.execute("""
        create table ihrms.payslip (
            id                uuid primary key default gen_random_uuid(),
            tenant_id         text not null default 'atvantiq',
            run_id            uuid not null references ihrms.payroll_run(id) on delete cascade,
            employee_id       bigint not null,
            lop_days          numeric(4,1) not null default 0,
            earnings          jsonb not null default '{}',
            deductions        jsonb not null default '{}',
            employer_contributions jsonb not null default '{}',
            gross             numeric(12,2) not null,
            total_deductions  numeric(12,2) not null,
            net_pay           numeric(12,2) not null,
            created_at        timestamptz not null default now(),
            unique (run_id, employee_id)
        )
    """)
    op.execute("create index ix_payslip_emp on ihrms.payslip (tenant_id, employee_id)")

    for t in _RLS_TABLES:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.payslip")
    op.execute("drop table if exists ihrms.payroll_run")
    op.execute("drop table if exists ihrms.salary_structure")
