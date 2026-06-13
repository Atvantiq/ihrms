"""Compensation bands & grades (M1 org engine)

Revision ID: 0031
Revises: 0030
Create Date: 2026-06-13

Salary bands (level + CTC range) and one current band per employee. Gives the
org a comp structure and a guardrail for salary changes. Tenant-scoped, RLS.
"""

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

_RLS = ["salary_band", "employee_band"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.salary_band (
            id         uuid primary key default gen_random_uuid(),
            tenant_id  text not null default 'atvantiq',
            code       text not null,
            name       text not null,
            level      int not null default 1,
            min_ctc    numeric(12,2) not null,
            max_ctc    numeric(12,2) not null,
            is_active  boolean not null default true,
            created_at timestamptz not null default now(),
            unique (tenant_id, code)
        )
    """)
    op.execute("""
        create table ihrms.employee_band (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            band_id     uuid not null references ihrms.salary_band(id),
            assigned_on date not null default current_date,
            assigned_by bigint,
            unique (tenant_id, employee_id)
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
    op.execute("""
        insert into ihrms.salary_band (code, name, level, min_ctc, max_ctc) values
          ('L1', 'Associate', 1,  400000, 800000),
          ('L2', 'Engineer', 2,  800000, 1600000),
          ('L3', 'Senior Engineer', 3, 1500000, 2800000),
          ('L4', 'Lead / Manager', 4, 2500000, 4500000),
          ('L5', 'Director', 5, 4000000, 8000000)
    """)


def downgrade() -> None:
    op.execute("drop table if exists ihrms.employee_band")
    op.execute("drop table if exists ihrms.salary_band")
