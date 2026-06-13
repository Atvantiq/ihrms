"""Announcements (Track-B TB3) — platform → tenant broadcast

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-13

Platform owners broadcast announcements (maintenance, releases, notices)
that every tenant user sees on their dashboard. Platform-level (not
tenant-scoped); super_admin authors, all authenticated users read active ones.
"""

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.announcement (
            id           uuid primary key default gen_random_uuid(),
            title        text not null,
            body         text not null,
            level        text not null default 'info'
                         check (level in ('info','success','warning')),
            is_active    boolean not null default true,
            created_by   bigint,
            created_at   timestamptz not null default now()
        )
    """)
    op.execute("create index ix_announcement_active on ihrms.announcement (is_active, created_at desc)")


def downgrade() -> None:
    op.execute("drop table if exists ihrms.announcement")
