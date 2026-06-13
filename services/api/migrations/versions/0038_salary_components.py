"""Configurable salary components (M3 — Salary config tabs)

Revision ID: 0038
Revises: 0037
Create Date: 2026-06-13

A component catalogue (earnings / reimbursements / deductions / employer) with
calc types (fixed, %CTC, %basic, %gross, balancing), tax treatment and
statutory wage flags. Drives a configurable structure preview. The live monthly
run keeps its standard split; this is the configurator layer. Tenant-scoped RLS.
"""

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.salary_component (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            code           text not null,
            name           text not null,
            component_type text not null
                           check (component_type in ('earning','reimbursement',
                                                     'deduction','employer')),
            calc_type      text not null
                           check (calc_type in ('fixed','pct_ctc','pct_basic',
                                                'pct_gross','balancing')),
            value          numeric(12,2) not null default 0,
            tax_treatment  text not null default 'taxable'
                           check (tax_treatment in ('taxable','partial','exempt')),
            pf_wage        boolean not null default false,
            esi_wage       boolean not null default false,
            pt_wage        boolean not null default false,
            on_payslip     boolean not null default true,
            is_active      boolean not null default true,
            sort_order     int not null default 100,
            unique (tenant_id, code)
        )
    """)
    op.execute("alter table ihrms.salary_component enable row level security")
    op.execute("alter table ihrms.salary_component force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.salary_component
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )
    # standard FY25-26 earning set — mirrors the built-in 40% basic / 50% HRA split
    op.execute("""
        insert into ihrms.salary_component
          (code, name, component_type, calc_type, value, tax_treatment,
           pf_wage, esi_wage, pt_wage, sort_order) values
          ('BASIC','Basic','earning','pct_ctc',40,'taxable',true,true,true,10),
          ('HRA','House Rent Allowance','earning','pct_basic',50,'partial',false,true,true,20),
          ('SPECIAL','Special Allowance','earning','balancing',0,'taxable',false,true,true,90)
    """)


def downgrade() -> None:
    op.execute("drop table if exists ihrms.salary_component")
