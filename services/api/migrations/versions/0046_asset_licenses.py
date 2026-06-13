"""Software licenses (seat tracking) + lost-asset register

Revision ID: 0046
Revises: 0045
Create Date: 2026-06-13

Software licenses with a seat count and per-employee seat assignments, plus a
lost-asset register capturing the circumstances when an asset is marked lost.
Tenant-scoped RLS; HR-managed.
"""

from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None

_TABLES = ("software_license", "license_seat", "asset_lost")


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
        create table ihrms.software_license (
            id           uuid primary key default gen_random_uuid(),
            tenant_id    text not null default 'atvantiq',
            name         text not null,
            vendor       text,
            seats_total  int not null default 1 check (seats_total >= 0),
            renewal_date date,
            cost_annual  numeric(12,2) not null default 0,
            notes        text,
            created_at   timestamptz not null default now()
        )
    """)
    op.execute("""
        create table ihrms.license_seat (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            license_id  uuid not null references ihrms.software_license(id) on delete cascade,
            employee_id bigint not null,
            assigned_on date not null default current_date,
            status      text not null default 'active'
                        check (status in ('active','revoked')),
            created_at  timestamptz not null default now()
        )
    """)
    op.execute("create index ix_license_seat_lic on ihrms.license_seat (license_id)")
    op.execute("""
        create table ihrms.asset_lost (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            asset_id      uuid not null references ihrms.asset(id) on delete cascade,
            reported_on   date not null default current_date,
            circumstances text not null,
            police_report boolean not null default false,
            created_by    bigint,
            created_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_asset_lost_asset on ihrms.asset_lost (asset_id)")

    for t in _TABLES:
        _rls(t)


def downgrade() -> None:
    for t in reversed(_TABLES):
        op.execute(f"drop table if exists ihrms.{t}")
