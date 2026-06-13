"""Tax regime + chapter VI-A declarations on salary structure

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-13

Adds the per-employee tax regime (new = default) and the declared
Chapter VI-A deductions (80C etc., old regime only) the TDS engine needs.
Stored on the active salary structure. ihrms-schema only.
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "alter table ihrms.salary_structure "
        "add column tax_regime text not null default 'new' "
        "check (tax_regime in ('new', 'old'))"
    )
    op.execute(
        "alter table ihrms.salary_structure "
        "add column chapter_via_deductions numeric(12,2) not null default 0"
    )


def downgrade() -> None:
    op.execute("alter table ihrms.salary_structure drop column chapter_via_deductions")
    op.execute("alter table ihrms.salary_structure drop column tax_regime")
