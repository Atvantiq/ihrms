"""Recruitment / ATS: requisitions, candidates, interviews, offers

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-13

Talent Acquisition (Milestone 4). A requisition holds open positions;
candidates move through a pipeline (applied→screening→interview→offer→
hired/rejected) with BGV; an accepted offer is onboarded into the shared
employee master (no re-entry). Tenant-scoped + RLS like the other tables.
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_RLS = ["requisition", "candidate", "interview", "offer"]


def upgrade() -> None:
    op.execute("""
        create table ihrms.requisition (
            id               uuid primary key default gen_random_uuid(),
            tenant_id        text not null default 'atvantiq',
            code             text not null,
            title            text not null,
            department       text,
            location         text,
            openings         int not null default 1,
            status           text not null default 'open'
                             check (status in ('draft','open','on_hold','closed')),
            hiring_manager_id bigint,
            created_by       bigint,
            created_at       timestamptz not null default now(),
            updated_at       timestamptz not null default now()
        )
    """)
    op.execute("create unique index ux_req_code on ihrms.requisition (tenant_id, code)")

    op.execute("""
        create table ihrms.candidate (
            id             uuid primary key default gen_random_uuid(),
            tenant_id      text not null default 'atvantiq',
            requisition_id uuid not null references ihrms.requisition(id),
            name           text not null,
            email          text not null,
            phone          text,
            source         text default 'direct',
            stage          text not null default 'applied'
                           check (stage in ('applied','screening','interview',
                                            'offer','hired','rejected')),
            rating         int check (rating between 1 and 5),
            bgv_status     text not null default 'not_started'
                           check (bgv_status in ('not_started','consent','in_progress',
                                                 'clear','flagged')),
            note           text,
            onboarded_employee_id bigint,
            created_at     timestamptz not null default now(),
            updated_at     timestamptz not null default now()
        )
    """)
    op.execute("create index ix_candidate_req on ihrms.candidate (tenant_id, requisition_id)")
    op.execute("create index ix_candidate_stage on ihrms.candidate (tenant_id, stage)")

    op.execute("""
        create table ihrms.interview (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            candidate_id  uuid not null references ihrms.candidate(id) on delete cascade,
            round         text not null,
            interviewer_id bigint,
            scheduled_at  timestamptz,
            recommendation text check (recommendation in ('yes','no','maybe')),
            feedback      text,
            created_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_interview_cand on ihrms.interview (tenant_id, candidate_id)")

    op.execute("""
        create table ihrms.offer (
            id            uuid primary key default gen_random_uuid(),
            tenant_id     text not null default 'atvantiq',
            candidate_id  uuid not null references ihrms.candidate(id) on delete cascade,
            designation   text not null,
            department    text not null,
            ctc_annual    numeric(12,2) not null,
            joining_date  date not null,
            status        text not null default 'draft'
                          check (status in ('draft','sent','accepted','declined')),
            created_by    bigint,
            created_at    timestamptz not null default now(),
            updated_at    timestamptz not null default now()
        )
    """)
    op.execute("create index ix_offer_cand on ihrms.offer (tenant_id, candidate_id)")

    for t in _RLS:
        op.execute(f"alter table ihrms.{t} enable row level security")
        op.execute(f"alter table ihrms.{t} force row level security")
        op.execute(
            f"""create policy tenant_isolation on ihrms.{t}
                using (tenant_id = current_setting('app.tenant_id', true))
                with check (tenant_id = current_setting('app.tenant_id', true))"""
        )


def downgrade() -> None:
    op.execute("drop table if exists ihrms.offer")
    op.execute("drop table if exists ihrms.interview")
    op.execute("drop table if exists ihrms.candidate")
    op.execute("drop table if exists ihrms.requisition")
