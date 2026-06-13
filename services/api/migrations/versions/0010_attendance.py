"""Attendance records

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-13

iHRMS owns its own attendance marks (present/absent/wfh) in the ihrms schema.
A day's effective status is DERIVED at read time by combining these marks
with approved leave, the holiday calendar, and weekends — so leave/holiday/
weekend days are never duplicated as rows. The monthly summary yields the
LOP count that payroll consumes. Tenant-scoped + RLS like the other tables.
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.attendance_record (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            work_date   date not null,
            status      text not null check (status in ('present', 'absent', 'wfh')),
            note        text,
            marked_by   bigint,
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now(),
            unique (tenant_id, employee_id, work_date)
        )
    """)
    op.execute(
        "create index ix_attendance_emp_date on ihrms.attendance_record "
        "(tenant_id, employee_id, work_date)"
    )
    op.execute("alter table ihrms.attendance_record enable row level security")
    op.execute("alter table ihrms.attendance_record force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.attendance_record
           using (tenant_id = current_setting('app.tenant_id', true))
           with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.attendance_record")
