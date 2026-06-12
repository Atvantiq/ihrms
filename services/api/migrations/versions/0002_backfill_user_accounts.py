"""Backfill ihrms.user_account from auth.users matched to employees by email

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12

Data-only migration; reads auth.users/public.employees, writes only ihrms.*.
- Every auth user whose email matches an employee gets a linked account
  with the default `employee` role.
- The ADMIN235 account (admin@yopmail.com) is seeded as hr_admin.
- Future users are linked just-in-time at first login (see security.py).
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        insert into ihrms.user_account (auth_user_id, employee_id, roles, persona)
        select distinct on (u.id) u.id, e.employee_id,
               case when lower(u.email) = 'admin@yopmail.com'
                    then array['employee','hr_admin'] else array['employee'] end,
               case when lower(u.email) = 'admin@yopmail.com'
                    then 'hr' else 'employee' end
        from auth.users u
        join public.employees e on lower(e.email) = lower(u.email)
        order by u.id, e.created_at
        on conflict (auth_user_id) do nothing
    """)


def downgrade() -> None:
    op.execute("delete from ihrms.user_account")
