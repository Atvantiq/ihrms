"""Feedback & recognition (M5)

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-13

Peer feedback (private) and recognition (public kudos with a value badge). A
lightweight culture layer alongside formal reviews. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.feedback (
            id               uuid primary key default gen_random_uuid(),
            tenant_id        text not null default 'atvantiq',
            from_employee_id bigint not null,
            to_employee_id   bigint not null,
            kind             text not null
                             check (kind in ('feedback','recognition')),
            badge            text,
            visibility       text not null default 'private'
                             check (visibility in ('private','public')),
            message          text not null,
            created_at       timestamptz not null default now(),
            check (from_employee_id <> to_employee_id)
        )
    """)
    op.execute("create index ix_feedback_to on ihrms.feedback (tenant_id, to_employee_id)")
    op.execute("create index ix_feedback_from on ihrms.feedback (tenant_id, from_employee_id)")
    op.execute("alter table ihrms.feedback enable row level security")
    op.execute("alter table ihrms.feedback force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.feedback
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.feedback")
