"""Employee personal records — the Employee 360 sub-tabs

Revision ID: 0039
Revises: 0038
Create Date: 2026-06-13

Family & nominees, education, prior experience, awards, training and
incidents (disciplinary / accident / safety). All are employee-scoped child
records: tenant-isolated via RLS, audited on write, surfaced read-only to the
employee themselves and read-write to HR. Special dates (birthday / work
anniversary) are derived from DOB / DOJ at read time, not stored here.
"""

from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

_TABLES = ("employee_family", "employee_education", "employee_experience",
           "employee_award", "employee_training", "employee_incident")


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
        create table ihrms.employee_family (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            employee_id   bigint not null,
            relation      text not null
                          check (relation in ('spouse','child','father','mother',
                                              'sibling','guardian','other')),
            full_name     text not null,
            date_of_birth date,
            gender        text,
            is_dependent  boolean not null default false,
            is_nominee    boolean not null default false,
            nominee_share numeric(5,2) not null default 0
                          check (nominee_share >= 0 and nominee_share <= 100),
            contact       text,
            created_at    timestamptz not null default now(),
            created_by    bigint
        )
    """)
    op.execute("""
        create table ihrms.employee_education (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            employee_id    bigint not null,
            degree         text not null,
            specialization text,
            institution    text,
            year_completed int,
            grade          text,
            created_at     timestamptz not null default now(),
            created_by     bigint
        )
    """)
    op.execute("""
        create table ihrms.employee_experience (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            employee_id  bigint not null,
            employer     text not null,
            designation  text,
            from_date    date,
            to_date      date,
            summary      text,
            created_at   timestamptz not null default now(),
            created_by   bigint
        )
    """)
    op.execute("""
        create table ihrms.employee_award (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            title       text not null,
            category    text,
            awarded_on  date,
            citation    text,
            created_at  timestamptz not null default now(),
            created_by  bigint
        )
    """)
    op.execute("""
        create table ihrms.employee_training (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            employee_id  bigint not null,
            program      text not null,
            provider     text,
            status       text not null default 'planned'
                         check (status in ('planned','in_progress','completed','cancelled')),
            completed_on date,
            created_at   timestamptz not null default now(),
            created_by   bigint
        )
    """)
    op.execute("""
        create table ihrms.employee_incident (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            employee_id   bigint not null,
            kind          text not null
                          check (kind in ('disciplinary','accident')),
            incident_date date not null,
            category      text,
            severity      text not null default 'low'
                          check (severity in ('low','medium','high')),
            description   text not null,
            action_taken  text,
            status        text not null default 'open'
                          check (status in ('open','closed')),
            created_at    timestamptz not null default now(),
            created_by    bigint
        )
    """)
    for t in _TABLES:
        op.execute(f"create index on ihrms.{t} (employee_id)")
        _rls(t)


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.execute(f"drop table if exists ihrms.{t}")
