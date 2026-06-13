"""Performance Improvement Plans (M5)

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-13

A structured PIP: objectives, a review window, periodic checkpoints, and an
outcome (improved / extended / terminated / closed). Tenant-scoped with RLS.
"""

from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

_RLS = ["pip", "pip_checkpoint"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.pip (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            manager_id  bigint,
            reason      text not null,
            objectives  text not null,
            start_date  date not null,
            end_date    date not null,
            status      text not null default 'active'
                        check (status in ('active','improved','extended','terminated','closed')),
            created_by  bigint,
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now()
        )
    """)
    op.execute("create index ix_pip_emp on ihrms.pip (tenant_id, employee_id, status)")

    op.execute("""
        create table ihrms.pip_checkpoint (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            pip_id         uuid not null references ihrms.pip(id) on delete cascade,
            checkpoint_date date not null default current_date,
            rating         text not null
                           check (rating in ('on_track','at_risk','off_track')),
            note           text,
            created_by     bigint,
            created_at     timestamptz not null default now()
        )
    """)
    op.execute("create index ix_pipcp_pip on ihrms.pip_checkpoint (tenant_id, pip_id)")

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.pip_checkpoint")
    op.execute("drop table if exists ihrms.pip")
