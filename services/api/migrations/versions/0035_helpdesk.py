"""Helpdesk / employee request tickets (M1)

Revision ID: 0035
Revises: 0034
Create Date: 2026-06-13

Employees raise tickets (payroll, leave, IT, facilities, HR policy, …); HR
assigns and resolves them. A simple case lifecycle. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.ticket (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            category    text not null
                        check (category in ('payroll','leave','it','facilities','hr_policy','other')),
            subject     text not null,
            description text not null,
            priority    text not null default 'medium'
                        check (priority in ('low','medium','high')),
            status      text not null default 'open'
                        check (status in ('open','in_progress','resolved','closed')),
            assignee_id bigint,
            resolution  text,
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now(),
            resolved_at timestamptz
        )
    """)
    op.execute("create index ix_ticket_emp on ihrms.ticket (tenant_id, employee_id, status)")
    op.execute("create index ix_ticket_status on ihrms.ticket (tenant_id, status)")
    op.execute("alter table ihrms.ticket enable row level security")
    op.execute("alter table ihrms.ticket force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.ticket
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.ticket")
