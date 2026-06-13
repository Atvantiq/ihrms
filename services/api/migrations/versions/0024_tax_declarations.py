"""Tax / investment declarations (M3 backlog)

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-13

Employees declare Chapter VI-A investments (80C, 80D, NPS, home-loan interest)
for a financial year. Once approved, the capped eligible deduction flows into
the TDS engine (old regime), lowering monthly tax. Proof upload is deferred
(needs document storage). Tenant-scoped with RLS.
"""

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

_RLS = ["tax_declaration", "tax_declaration_item"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.tax_declaration (
            id          uuid primary key default gen_random_uuid(),
            tenant_id   text not null default 'atvantiq',
            employee_id bigint not null,
            fy          text not null,
            regime      text not null default 'old'
                        check (regime in ('old','new')),
            status      text not null default 'draft'
                        check (status in ('draft','submitted','approved','rejected')),
            decided_by  bigint,
            decided_at  timestamptz,
            created_at  timestamptz not null default now(),
            updated_at  timestamptz not null default now(),
            unique (tenant_id, employee_id, fy)
        )
    """)
    op.execute("create index ix_taxdecl_emp on ihrms.tax_declaration (tenant_id, employee_id)")

    op.execute("""
        create table ihrms.tax_declaration_item (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            declaration_id uuid not null
                           references ihrms.tax_declaration(id) on delete cascade,
            section        text not null,
            amount         numeric(12,2) not null default 0 check (amount >= 0),
            unique (declaration_id, section)
        )
    """)

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.tax_declaration_item")
    op.execute("drop table if exists ihrms.tax_declaration")
