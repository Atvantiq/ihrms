"""Onboarding task templates + per-hire checklists

Revision ID: 0044
Revises: 0043
Create Date: 2026-06-13

A master onboarding template (ordered tasks, each owned by a role) that is
instantiated into a per-employee checklist when a new hire joins. Drives the
onboarding-progress view. Tenant-scoped RLS; seeded with a standard checklist.
"""

from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None

_TABLES = ("onboarding_template_task", "onboarding_task")


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
        create table ihrms.onboarding_template_task (
            id         uuid primary key default gen_random_uuid(),
            tenant_id  text not null default 'atvantiq',
            title      text not null,
            owner_role text not null default 'hr'
                       check (owner_role in ('hr','manager','it','employee')),
            sort_order int not null default 100,
            is_active  boolean not null default true,
            created_at timestamptz not null default now()
        )
    """)
    op.execute("""
        create table ihrms.onboarding_task (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            employee_id  bigint not null,
            title        text not null,
            owner_role   text not null default 'hr',
            status       text not null default 'pending'
                         check (status in ('pending','done')),
            completed_on date,
            sort_order   int not null default 100,
            created_at   timestamptz not null default now()
        )
    """)
    op.execute("create index ix_onboarding_task_emp on ihrms.onboarding_task (employee_id)")

    # standard onboarding checklist (ASCII-only seeds for C-locale test DB)
    op.execute("""
        insert into ihrms.onboarding_template_task (title, owner_role, sort_order) values
          ('Sign offer & employment contract', 'hr', 10),
          ('Submit ID & statutory documents', 'employee', 20),
          ('Provision laptop & system accounts', 'it', 30),
          ('Add to payroll & benefits', 'hr', 40),
          ('Team introduction & buddy assignment', 'manager', 50),
          ('Complete mandatory policy acknowledgements', 'employee', 60)
    """)

    for t in _TABLES:
        _rls(t)


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.execute(f"drop table if exists ihrms.{t}")
