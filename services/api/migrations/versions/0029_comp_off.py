"""Compensatory off (comp-off) ledger (M2)

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-13

Working a holiday or weekend earns a comp-off credit (manager-approved, with an
expiry). The employee later avails it as a day off. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.comp_off (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            employee_id  bigint not null,
            earned_date  date not null,
            reason       text not null,
            status       text not null default 'pending'
                         check (status in ('pending','approved','rejected','availed','expired')),
            expiry_date  date,
            availed_on   date,
            decided_by   bigint,
            decided_at   timestamptz,
            created_at   timestamptz not null default now(),
            unique (tenant_id, employee_id, earned_date)
        )
    """)
    op.execute("create index ix_compoff_emp on ihrms.comp_off (tenant_id, employee_id, status)")
    op.execute("alter table ihrms.comp_off enable row level security")
    op.execute("alter table ihrms.comp_off force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.comp_off
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.comp_off")
