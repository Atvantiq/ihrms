"""Asset register & assignments (Finance/Assets)

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-13

Company assets (laptops, phones, …) and who holds them. Assignment is a
lifecycle: an asset is issued to an employee and returned on exit, which feeds
the F&F clearance. Tenant-scoped with RLS like the rest of the HR data.
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

_RLS = ["asset", "asset_assignment"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.asset (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            asset_tag     text not null,
            category      text not null default 'laptop'
                          check (category in ('laptop','desktop','phone','monitor',
                                              'peripheral','furniture','other')),
            name          text not null,
            serial_no     text,
            purchase_date date,
            purchase_cost numeric(12,2),
            status        text not null default 'in_stock'
                          check (status in ('in_stock','assigned','retired','lost')),
            condition     text not null default 'good'
                          check (condition in ('new','good','fair','poor')),
            note          text,
            created_at    timestamptz not null default now(),
            updated_at    timestamptz not null default now()
        )
    """)
    op.execute("create unique index ux_asset_tag on ihrms.asset (tenant_id, asset_tag)")

    op.execute("""
        create table ihrms.asset_assignment (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            asset_id      uuid not null references ihrms.asset(id) on delete cascade,
            employee_id   bigint not null,
            assigned_on   date not null default current_date,
            returned_on   date,
            status        text not null default 'assigned'
                          check (status in ('assigned','returned')),
            note          text,
            created_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_assignment_emp on ihrms.asset_assignment (tenant_id, employee_id)")
    op.execute("create index ix_assignment_asset on ihrms.asset_assignment (tenant_id, asset_id)")
    # one open assignment per asset at a time
    op.execute(
        "create unique index ux_assignment_open on ihrms.asset_assignment "
        "(asset_id) where status = 'assigned'"
    )

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.asset_assignment")
    op.execute("drop table if exists ihrms.asset")
