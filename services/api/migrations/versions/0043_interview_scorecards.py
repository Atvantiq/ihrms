"""Interview scorecards — structured per-criterion scoring

Revision ID: 0043
Revises: 0042
Create Date: 2026-06-13

Each interview gets a scorecard: one row per evaluation criterion (technical,
communication, culture fit, …) scored 1-5 with an optional comment. A
candidate's scorecard aggregates these across all their interviews into a
per-criterion average and an overall score. Tenant-scoped RLS.
"""

from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.interview_score (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            interview_id uuid not null references ihrms.interview(id) on delete cascade,
            criterion    text not null,
            score        int not null check (score between 1 and 5),
            comment      text,
            created_at   timestamptz not null default now()
        )
    """)
    op.execute("create index ix_iscore_interview on ihrms.interview_score (interview_id)")
    op.execute("alter table ihrms.interview_score enable row level security")
    op.execute("alter table ihrms.interview_score force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.interview_score
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.interview_score")
