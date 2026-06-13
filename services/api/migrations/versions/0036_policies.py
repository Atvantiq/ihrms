"""Policies & acknowledgements (M1)

Revision ID: 0036
Revises: 0035
Create Date: 2026-06-13

HR publishes policy documents (versioned); employees acknowledge them; HR
tracks acknowledgement compliance. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

_RLS = ["policy", "policy_ack"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.policy (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            title        text not null,
            category     text not null default 'general',
            body         text not null,
            version      int not null default 1,
            is_active    boolean not null default true,
            published_at timestamptz not null default now(),
            created_by   bigint
        )
    """)
    op.execute("""
        create table ihrms.policy_ack (
            id              uuid primary key default gen_random_uuid(),
            tenant_id       text not null default 'atvantiq',
            policy_id       uuid not null references ihrms.policy(id) on delete cascade,
            employee_id     bigint not null,
            acknowledged_at timestamptz not null default now(),
            unique (policy_id, employee_id)
        )
    """)
    op.execute("create index ix_policyack_pol on ihrms.policy_ack (tenant_id, policy_id)")

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.policy_ack")
    op.execute("drop table if exists ihrms.policy")
