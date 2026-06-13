"""Periodic check-ins (M5)

Revision ID: 0032
Revises: 0031
Create Date: 2026-06-13

Lightweight periodic self-reflections (highlights, challenges, mood) that an
employee logs and their manager can read. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.check_in (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            employee_id   bigint not null,
            check_in_date date not null default current_date,
            highlights    text not null,
            challenges    text,
            mood          int not null check (mood between 1 and 5),
            created_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_checkin_emp on ihrms.check_in (tenant_id, employee_id, check_in_date desc)")
    op.execute("alter table ihrms.check_in enable row level security")
    op.execute("alter table ihrms.check_in force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.check_in
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.check_in")
