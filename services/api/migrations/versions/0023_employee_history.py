"""Effective-dated employee change history (M1 backlog)

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-13

An append-only log of changes to an employee's record — promotions, transfers,
manager changes, compensation revisions — so the profile shows a timeline and
changes are auditable beyond the generic audit log. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.employee_history (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            employee_id    bigint not null,
            category       text not null
                           check (category in ('job','personal','compensation')),
            field          text not null,
            old_value      text,
            new_value      text,
            effective_date date not null default current_date,
            changed_by     bigint,
            note           text,
            created_at     timestamptz not null default now()
        )
    """)
    op.execute(
        "create index ix_history_emp on ihrms.employee_history "
        "(tenant_id, employee_id, created_at desc)"
    )
    op.execute("alter table ihrms.employee_history enable row level security")
    op.execute("alter table ihrms.employee_history force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.employee_history
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.employee_history")
