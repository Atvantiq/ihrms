"""Career ladders + competency framework

Revision ID: 0045
Revises: 0044
Create Date: 2026-06-13

Career tracks made of ranked levels (the ladder), a competency framework, and
per-level competency expectations (what 'good' looks like at each rung).
Employees are placed on a level. Drives the "my career ladder" growth view.
Tenant-scoped RLS; seeded with a sample engineering track + competencies.
"""

from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None

_TABLES = (
    "career_track", "career_level", "competency",
    "level_competency", "employee_career_level",
)


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
        create table ihrms.career_track (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            name        text not null,
            description text,
            created_at  timestamptz not null default now(),
            unique (tenant_id, name)
        )
    """)
    op.execute("""
        create table ihrms.career_level (
            id        uuid primary key default gen_random_uuid(),
            tenant_id text not null default 'atvantiq',
            track_id  uuid not null references ihrms.career_track(id) on delete cascade,
            name      text not null,
            rank      int not null,
            summary   text,
            unique (track_id, rank)
        )
    """)
    op.execute("create index ix_career_level_track on ihrms.career_level (track_id)")
    op.execute("""
        create table ihrms.competency (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            name        text not null,
            category    text,
            description text,
            unique (tenant_id, name)
        )
    """)
    op.execute("""
        create table ihrms.level_competency (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            level_id      uuid not null references ihrms.career_level(id) on delete cascade,
            competency_id uuid not null references ihrms.competency(id) on delete cascade,
            expectation   text not null,
            unique (level_id, competency_id)
        )
    """)
    op.execute("create index ix_levelcomp_level on ihrms.level_competency (level_id)")
    op.execute("""
        create table ihrms.employee_career_level (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            level_id    uuid not null references ihrms.career_level(id) on delete cascade,
            placed_on   date not null default current_date,
            unique (tenant_id, employee_id)
        )
    """)

    # sample engineering ladder + competencies (ASCII-only seeds for C-locale)
    op.execute(
        "insert into ihrms.career_track (name, description) values "
        "('Engineering', 'Individual-contributor engineering track')"
    )
    op.execute("""
        insert into ihrms.career_level (track_id, name, rank, summary)
        select t.id, v.name, v.rank, v.summary
        from ihrms.career_track t,
          (values ('Engineer', 1, 'Delivers well-scoped tasks with guidance'),
                  ('Senior Engineer', 2, 'Owns features end to end'),
                  ('Staff Engineer', 3, 'Drives cross-team technical direction'),
                  ('Principal Engineer', 4, 'Sets org-wide technical strategy')
          ) as v(name, rank, summary)
        where t.name = 'Engineering'
    """)
    op.execute("""
        insert into ihrms.competency (name, category, description) values
          ('Technical depth', 'craft', 'Mastery of the tools and systems'),
          ('Collaboration', 'people', 'Works effectively across the team'),
          ('Ownership', 'impact', 'Drives outcomes end to end')
    """)

    for t in _TABLES:
        _rls(t)


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.execute(f"drop table if exists ihrms.{t}")
