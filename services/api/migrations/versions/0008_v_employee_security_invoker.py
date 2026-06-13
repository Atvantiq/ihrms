"""v_employee runs with the caller's privileges (security_invoker)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-13

Captures, as a migration, the security_invoker setting applied to
ihrms.v_employee during the RLS cutover (previously a manual ALTER on the
dev DB). With security_invoker the view's joins to ihrms.user_account are
evaluated under the caller's RLS, so tenant isolation holds through the
view. Requires the app role to hold SELECT on the underlying public.*
tables (granted to ihrms_app; superuser in tests). Idempotent.
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("alter view ihrms.v_employee set (security_invoker = true)")


def downgrade() -> None:
    op.execute("alter view ihrms.v_employee reset (security_invoker)")
