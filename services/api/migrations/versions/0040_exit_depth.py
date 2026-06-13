"""Exit depth — KT checklist, exit interview, alumni / rehire register

Revision ID: 0040
Revises: 0039
Create Date: 2026-06-13

Layers the deeper Exit tabs on top of the existing case → clearance → F&F flow:
a knowledge-transfer checklist, a structured exit interview (one per case) and
an alumni / rehire register. Exit analytics (attrition, reasons, avg tenure at
exit) are derived at read time from the case set, not stored. Tenant-scoped RLS.
"""

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

_TABLES = ("exit_kt_item", "exit_interview", "exit_alumni")


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
        create table ihrms.exit_kt_item (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            exit_case_id uuid not null references ihrms.exit_case(id) on delete cascade,
            task         text not null,
            assignee     text,
            status       text not null default 'pending'
                         check (status in ('pending','done')),
            note         text,
            created_at   timestamptz not null default now(),
            updated_at   timestamptz not null default now()
        )
    """)
    op.execute("create index ix_kt_case on ihrms.exit_kt_item (exit_case_id)")

    op.execute("""
        create table ihrms.exit_interview (
            id                uuid primary key default gen_random_uuid(),
            tenant_id         text not null default 'atvantiq',
            exit_case_id      uuid not null references ihrms.exit_case(id) on delete cascade,
            primary_reason    text,
            would_recommend   boolean,
            rating_management int check (rating_management between 1 and 5),
            rating_role       int check (rating_role between 1 and 5),
            rating_culture    int check (rating_culture between 1 and 5),
            feedback          text,
            conducted_on      date,
            conducted_by      bigint,
            created_at        timestamptz not null default now(),
            unique (exit_case_id)
        )
    """)

    op.execute("""
        create table ihrms.exit_alumni (
            id                  uuid primary key default gen_random_uuid(),
            tenant_id           text not null default 'atvantiq',
            employee_id         bigint not null,
            exit_case_id        uuid references ihrms.exit_case(id) on delete set null,
            eligible_for_rehire boolean not null default true,
            personal_email      text,
            note                text,
            created_at          timestamptz not null default now(),
            unique (tenant_id, employee_id)
        )
    """)

    for t in _TABLES:
        _rls(t)


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.execute(f"drop table if exists ihrms.{t}")
