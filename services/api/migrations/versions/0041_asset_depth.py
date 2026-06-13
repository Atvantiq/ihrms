"""Asset depth — employee asset requests + maintenance log

Revision ID: 0041
Revises: 0040
Create Date: 2026-06-13

Two child surfaces on the asset register: an employee-raised asset request
(category + justification → HR approves/allocates or rejects) and a per-asset
maintenance log (service / repair / upgrade with cost). Tenant-scoped RLS;
writes audited. Approval optionally allocates a specific in-stock asset, which
the existing assign flow then books to the employee.
"""

from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None

_TABLES = ("asset_request", "asset_maintenance")


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
        create table ihrms.asset_request (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            employee_id   bigint not null,
            category      text not null
                          check (category in ('laptop','desktop','phone','monitor',
                                              'peripheral','furniture','other')),
            justification text not null,
            status        text not null default 'pending'
                          check (status in ('pending','approved','rejected','fulfilled')),
            allocated_asset_id uuid references ihrms.asset(id) on delete set null,
            decision_note text,
            decided_by    bigint,
            created_at    timestamptz not null default now(),
            updated_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_asset_request_emp on ihrms.asset_request (employee_id)")

    op.execute("""
        create table ihrms.asset_maintenance (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            asset_id     uuid not null references ihrms.asset(id) on delete cascade,
            kind         text not null default 'service'
                         check (kind in ('service','repair','upgrade','inspection')),
            performed_on date not null,
            cost         numeric(12,2) not null default 0,
            vendor       text,
            note         text,
            created_by   bigint,
            created_at   timestamptz not null default now()
        )
    """)
    op.execute("create index ix_asset_maint_asset on ihrms.asset_maintenance (asset_id)")

    for t in _TABLES:
        _rls(t)


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.execute(f"drop table if exists ihrms.{t}")
