"""Append-only audit trail

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13

Compliance requirement for HRMS: every write records who did what, to which
entity, when, with what changes, and the request_id for tracing. Append-only
by convention (app never updates/deletes); a future migration can add a
hash-chain + WORM archive per blueprint doc 20.
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.audit_event (
            id                 uuid primary key default gen_random_uuid(),
            tenant_id          text not null default 'atvantiq',
            actor_employee_id  bigint,
            actor_email        text,
            action             text not null,        -- e.g. employee.update, leave.approve
            entity_type        text not null,        -- employee | leave_request | org_master
            entity_id          text,
            summary            text,
            changes            jsonb not null default '{}',
            request_id         text,
            created_at         timestamptz not null default now()
        )
    """)
    op.execute(
        "create index ix_audit_entity on ihrms.audit_event "
        "(tenant_id, entity_type, entity_id, created_at desc)"
    )
    op.execute(
        "create index ix_audit_actor on ihrms.audit_event "
        "(tenant_id, actor_employee_id, created_at desc)"
    )
    op.execute("alter table ihrms.audit_event enable row level security")


def downgrade() -> None:
    op.execute("drop table if exists ihrms.audit_event")
