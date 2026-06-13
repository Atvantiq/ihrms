"""DPDP consent records (M1 backlog)

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-13

India's DPDP Act requires specific, informed, withdrawable consent per purpose
for processing personal data. This holds the current consent state per
(employee, purpose); the full grant/withdraw trail lives in the audit log.
Tenant-scoped with RLS.
"""

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.consent (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            purpose     text not null,
            status      text not null default 'granted'
                        check (status in ('granted','withdrawn')),
            version     int not null default 1,
            source      text not null default 'self'
                        check (source in ('self','hr')),
            decided_by  bigint,
            decided_at  timestamptz not null default now(),
            created_at  timestamptz not null default now(),
            unique (tenant_id, employee_id, purpose)
        )
    """)
    op.execute("create index ix_consent_emp on ihrms.consent (tenant_id, employee_id)")
    op.execute("alter table ihrms.consent enable row level security")
    op.execute("alter table ihrms.consent force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.consent
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.consent")
