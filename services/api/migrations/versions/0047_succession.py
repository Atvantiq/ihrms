"""Succession planning — key positions + successor readiness

Revision ID: 0047
Revises: 0046
Create Date: 2026-06-13

Critical positions (with their incumbent and vacancy risk) and a bench of
successor candidates, each with a readiness horizon. Drives the bench-strength
view. Tenant-scoped RLS; HR-managed.
"""

from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None

_TABLES = ("key_position", "succession_candidate")


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
        create table ihrms.key_position (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            title       text not null,
            incumbent_id bigint,
            risk_level  text not null default 'medium'
                        check (risk_level in ('low','medium','high')),
            notes       text,
            created_at  timestamptz not null default now()
        )
    """)
    op.execute("""
        create table ihrms.succession_candidate (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            position_id uuid not null references ihrms.key_position(id) on delete cascade,
            employee_id bigint not null,
            readiness   text not null default '1_2_years'
                        check (readiness in ('ready_now','1_2_years','3_5_years')),
            note        text,
            created_at  timestamptz not null default now(),
            unique (position_id, employee_id)
        )
    """)
    op.execute(
        "create index ix_succession_cand_pos on ihrms.succession_candidate (position_id)"
    )

    for t in _TABLES:
        _rls(t)


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.execute(f"drop table if exists ihrms.{t}")
