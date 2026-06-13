"""Out-on-duty / work-from-home requests (M2)

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-13

Forward-looking WFH / on-duty requests for a date range. On approval the
attendance records for those days are created automatically. Tenant-scoped, RLS.
"""

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.duty_request (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            duty_type   text not null check (duty_type in ('wfh','on_duty')),
            start_date  date not null,
            end_date    date not null,
            reason      text not null,
            status      text not null default 'pending'
                        check (status in ('pending','approved','rejected')),
            decided_by  bigint,
            decided_at  timestamptz,
            created_at  timestamptz not null default now()
        )
    """)
    op.execute("create index ix_duty_emp on ihrms.duty_request (tenant_id, employee_id, status)")
    op.execute("alter table ihrms.duty_request enable row level security")
    op.execute("alter table ihrms.duty_request force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.duty_request
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.duty_request")
