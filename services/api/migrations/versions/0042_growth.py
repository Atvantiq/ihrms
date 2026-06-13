"""Development plans, action items & mentorship (Performance growth tabs)

Revision ID: 0042
Revises: 0041
Create Date: 2026-06-13

The growth side of performance: individual development plans (a focus area +
objective + target date) with a checklist of action items, and mentorship
pairings. Plans are owned by the employee (self-service) and visible to HR;
mentorships are HR-managed. Tenant-scoped RLS; writes audited.
"""

from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

_TABLES = ("development_plan", "development_action", "mentorship")


def _rls(table: str) -> None:
    op.execute(f"alter table ihrms.{table} enable row level security")
    op.execute(f"alter table ihrms.{table} force row level security")
    op.execute(
        f"""create policy tenant_isolation on ihrms.{table}
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def upgrade() -> None:
    op.execute("""
        create table ihrms.development_plan (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            focus_area  text not null,
            objective   text not null,
            target_date date,
            status      text not null default 'active'
                        check (status in ('active','achieved','dropped')),
            created_by  bigint,
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now()
        )
    """)
    op.execute("create index ix_devplan_emp on ihrms.development_plan (employee_id)")

    op.execute("""
        create table ihrms.development_action (
            id         uuid primary key default gen_random_uuid(),
            tenant_id  text not null default 'atvantiq',
            plan_id    uuid not null references ihrms.development_plan(id) on delete cascade,
            action     text not null,
            status     text not null default 'pending'
                       check (status in ('pending','done')),
            created_at timestamptz not null default now()
        )
    """)
    op.execute("create index ix_devaction_plan on ihrms.development_action (plan_id)")

    op.execute("""
        create table ihrms.mentorship (
            id         uuid primary key default gen_random_uuid(),
            tenant_id  text not null default 'atvantiq',
            mentor_id  bigint not null,
            mentee_id  bigint not null,
            focus      text,
            status     text not null default 'active'
                       check (status in ('active','closed')),
            started_on date not null default current_date,
            created_at timestamptz not null default now()
        )
    """)
    op.execute("create index ix_mentorship_mentee on ihrms.mentorship (mentee_id)")

    for t in _TABLES:
        _rls(t)


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.execute(f"drop table if exists ihrms.{t}")
