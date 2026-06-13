"""Per-employee statutory identifiers (M3 backlog — for return files)

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-13

UAN (EPFO), ESIC IP number, PF member id and PT state per employee — needed to
generate the PF ECR, ESI contribution and PT return files. Kept in ihrms (not
the shared ONAQT tables). Tenant-scoped with RLS.
"""

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.employee_statutory (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            uan         text,
            pf_number   text,
            esic_ip     text,
            pt_state    text not null default 'KA',
            updated_by  bigint,
            updated_at  timestamptz not null default now(),
            unique (tenant_id, employee_id)
        )
    """)
    op.execute("alter table ihrms.employee_statutory enable row level security")
    op.execute("alter table ihrms.employee_statutory force row level security")
    op.execute(
        """create policy tenant_isolation on ihrms.employee_statutory
            using (tenant_id = current_setting('app.tenant_id', true))
            with check (tenant_id = current_setting('app.tenant_id', true))"""
    )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.employee_statutory")
