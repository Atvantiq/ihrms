"""Control plane (Track-B): plans, tenants, invoices, statutory packs

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-13

Platform-level tables describing ALL tenants — deliberately NOT tenant-RLS'd
(they are cross-tenant by nature); access is gated to super_admin at the API.
TB0 tenants/plans, TB1 billing (PEPM), TB2 statutory rate master. Seeds the
plan catalogue, the existing 'atvantiq' tenant, an FY25-26 statutory pack,
and grants admin@yopmail.com the super_admin role.
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.plan (
            code                 text primary key,
            name                 text not null,
            price_per_employee   numeric(8,2) not null,
            included_employees   int not null default 0,
            features             jsonb not null default '{}',
            is_active            boolean not null default true,
            created_at           timestamptz not null default now()
        )
    """)
    op.execute("""
        create table ihrms.tenant (
            id          text primary key,
            name        text not null,
            plan_code   text references ihrms.plan(code),
            status      text not null default 'trial'
                        check (status in ('trial','active','suspended','churned')),
            region      text not null default 'ap-south-1',
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now()
        )
    """)
    op.execute("""
        create table ihrms.invoice (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null references ihrms.tenant(id),
            period_year    int not null,
            period_month   int not null,
            employee_count int not null,
            rate           numeric(8,2) not null,
            amount         numeric(12,2) not null,
            status         text not null default 'issued'
                           check (status in ('draft','issued','paid')),
            created_at     timestamptz not null default now(),
            unique (tenant_id, period_year, period_month)
        )
    """)
    op.execute("""
        create table ihrms.statutory_pack (
            id            uuid primary key default gen_random_uuid(),
            name          text not null,
            country       text not null default 'IN',
            effective_from date not null,
            rates         jsonb not null,
            is_active     boolean not null default false,
            published_at  timestamptz,
            created_at    timestamptz not null default now()
        )
    """)

    op.execute("""
        insert into ihrms.plan (code, name, price_per_employee, included_employees, features) values
          ('starter','Starter', 49,  25, '{"payroll": true, "leave": true, "support": "email"}'),
          ('growth','Growth', 99,  100, '{"payroll": true, "performance": true, "recruitment": true, "support": "priority"}'),
          ('enterprise','Enterprise', 149, 500, '{"all": true, "sso": true, "support": "dedicated", "sla": "99.9"}')
    """)
    op.execute("""
        insert into ihrms.tenant (id, name, plan_code, status, region) values
          ('atvantiq','Atvantiq People','enterprise','active','ap-south-1')
    """)
    op.execute("""
        insert into ihrms.statutory_pack (name, effective_from, rates, is_active, published_at)
        values ('India FY2025-26', '2025-04-01', '{
          "pf_rate": 0.12, "pf_ceiling": 15000,
          "esi_employee": 0.0075, "esi_employer": 0.0325, "esi_gross_ceiling": 21000,
          "pt_amount": 200, "pt_exempt_below": 25000,
          "tds_regime_default": "new", "cess": 0.04, "gratuity_cap": 2000000
        }', true, now())
    """)

    # platform owner role (super_admin includes HR capabilities via principal)
    op.execute("""
        update ihrms.user_account set roles = array['employee','hr_admin','super_admin']
        where auth_user_id = '832131a4-746b-4fd9-8b41-6db94906e820'
    """)


def downgrade() -> None:
    op.execute("""update ihrms.user_account set roles = array['employee','hr_admin']
                  where auth_user_id = '832131a4-746b-4fd9-8b41-6db94906e820'""")
    op.execute("drop table if exists ihrms.statutory_pack")
    op.execute("drop table if exists ihrms.invoice")
    op.execute("drop table if exists ihrms.tenant")
    op.execute("drop table if exists ihrms.plan")
