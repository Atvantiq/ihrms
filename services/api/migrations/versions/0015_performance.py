"""Performance: review cycles, reviews, goals, increments

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-13

Milestone 5. A review cycle runs reviews (self→manager→published rating +
potential → 9-box); approved increments push into payroll (new salary
structure). Tenant-scoped + RLS.
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_RLS = ["review_cycle", "review", "goal", "increment"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.review_cycle (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            name         text not null,
            period_year  int not null,
            status       text not null default 'open'
                         check (status in ('open','calibration','published','closed')),
            created_by   bigint,
            created_at   timestamptz not null default now()
        )
    """)

    op.execute("""
        create table ihrms.review (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            cycle_id       uuid not null references ihrms.review_cycle(id) on delete cascade,
            employee_id    bigint not null,
            manager_id     bigint,
            self_rating    int check (self_rating between 1 and 5),
            self_comment   text,
            manager_rating int check (manager_rating between 1 and 5),
            manager_comment text,
            potential      int check (potential between 1 and 5),
            final_rating   int check (final_rating between 1 and 5),
            status         text not null default 'pending'
                           check (status in ('pending','self_done','manager_done','published')),
            created_at     timestamptz not null default now(),
            updated_at     timestamptz not null default now(),
            unique (tenant_id, cycle_id, employee_id)
        )
    """)
    op.execute("create index ix_review_emp on ihrms.review (tenant_id, employee_id)")

    op.execute("""
        create table ihrms.goal (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            employee_id  bigint not null,
            cycle_id     uuid references ihrms.review_cycle(id) on delete set null,
            title        text not null,
            description  text,
            progress     int not null default 0 check (progress between 0 and 100),
            status       text not null default 'active'
                         check (status in ('active','done','dropped')),
            created_at   timestamptz not null default now(),
            updated_at   timestamptz not null default now()
        )
    """)
    op.execute("create index ix_goal_emp on ihrms.goal (tenant_id, employee_id)")

    op.execute("""
        create table ihrms.increment (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            employee_id   bigint not null,
            cycle_id      uuid references ihrms.review_cycle(id) on delete set null,
            current_ctc   numeric(12,2) not null,
            proposed_ctc  numeric(12,2) not null,
            pct           numeric(5,2) not null,
            effective_date date not null,
            status        text not null default 'proposed'
                          check (status in ('proposed','approved','pushed')),
            approved_by   bigint,
            created_at    timestamptz not null default now(),
            updated_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_increment_emp on ihrms.increment (tenant_id, employee_id)")

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.increment")
    op.execute("drop table if exists ihrms.goal")
    op.execute("drop table if exists ihrms.review")
    op.execute("drop table if exists ihrms.review_cycle")
