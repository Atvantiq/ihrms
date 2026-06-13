"""Enforce tenant isolation via RLS (force + per-session GUC)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-13

Until now RLS was enabled but NOT enforced: the app connects as the table
owner, and owners bypass RLS. This makes tenant isolation real:

- FORCE ROW LEVEL SECURITY so even the owner connection is subject to policy
- a tenant_isolation policy: rows are visible/writable only when their
  tenant_id matches current_setting('app.tenant_id')
- the app sets app.tenant_id on every DB session (see core/db.get_session)

current_setting(..., true) returns NULL when unset, so a connection that
forgets to set the GUC sees NO rows (fail-closed) rather than all rows.
Only ihrms.* tenant tables are affected; ONAQT's public.* tables are
untouched. A dedicated non-superuser app role remains the recommended
defence-in-depth for production (see blueprint doc 20 / 24).
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_TENANT_TABLES = [
    "user_account",
    "org_masters",
    "org_value_map",
    "leave_type",
    "leave_balance",
    "leave_request",
    "audit_event",
]


def upgrade() -> None:
    for t in _TENANT_TABLES:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    for t in _TENANT_TABLES:
        op.execute(f"drop policy if exists tenant_isolation on ihrms.{t}")
        op.execute(f"alter table ihrms.{t} no force row level security")
