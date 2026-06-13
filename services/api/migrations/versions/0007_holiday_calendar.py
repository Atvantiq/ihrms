"""Holiday calendar

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-13

Public/optional holidays so leave working-day math (and later attendance/
payroll) excludes them, not just weekends. Tenant-scoped (RLS applies).
Seeds the fixed-date national holidays for 2026 on the atvantiq tenant;
HR adds festival/optional/region-specific ones via the UI.
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.holiday (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            name          text not null,
            holiday_date  date not null,
            type          text not null default 'public'
                          check (type in ('public', 'optional', 'restricted')),
            is_active     boolean not null default true,
            created_at    timestamptz not null default now(),
            updated_at    timestamptz not null default now()
        )
    """)
    op.execute(
        "create unique index ux_holiday_tenant_date_name "
        "on ihrms.holiday (tenant_id, holiday_date, name) where is_active"
    )
    op.execute("create index ix_holiday_date on ihrms.holiday (tenant_id, holiday_date)")
    op.execute("alter table ihrms.holiday enable row level security")
    op.execute("alter table ihrms.holiday force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.holiday
           using (tenant_id = current_setting('app.tenant_id', true))
           with check (tenant_id = current_setting('app.tenant_id', true))"""
    )

    # Fixed-date national holidays for 2026 (HR adds festival/region ones).
    op.execute("""
        insert into ihrms.holiday (name, holiday_date, type) values
          ('Republic Day',       '2026-01-26', 'public'),
          ('Independence Day',   '2026-08-15', 'public'),
          ('Gandhi Jayanti',     '2026-10-02', 'public'),
          ('Christmas',          '2026-12-25', 'public')
    """)


def downgrade() -> None:
    op.execute("drop table if exists ihrms.holiday")
