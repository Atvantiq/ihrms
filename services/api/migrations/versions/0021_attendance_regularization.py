"""Attendance regularization requests (M2 backlog)

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-13

An employee requests a correction for a day that's missing or wrong (forgot to
mark, was on duty, WFH). A manager/HR approves it, which writes the actual
attendance record. This puts an approval gate in front of self-marking, and the
pending requests surface in the unified task inbox. Tenant-scoped with RLS.
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.attendance_regularization (
            id               uuid primary key default gen_random_uuid(),
            tenant_id        text not null default 'atvantiq',
            employee_id      bigint not null,
            work_date        date not null,
            requested_status text not null
                             check (requested_status in ('present','wfh')),
            reason           text not null,
            status           text not null default 'pending'
                             check (status in ('pending','approved','rejected')),
            decided_by       bigint,
            decision_note    text,
            decided_at       timestamptz,
            created_at       timestamptz not null default now()
        )
    """)
    op.execute(
        "create index ix_regularization_emp on ihrms.attendance_regularization "
        "(tenant_id, employee_id, status)"
    )
    # at most one open request per employee per day
    op.execute(
        "create unique index ux_regularization_open on ihrms.attendance_regularization "
        "(employee_id, work_date) where status = 'pending'"
    )
    op.execute("alter table ihrms.attendance_regularization enable row level security")
    op.execute("alter table ihrms.attendance_regularization force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.attendance_regularization
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.attendance_regularization")
