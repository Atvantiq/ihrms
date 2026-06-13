"""Leave management — types, balances, requests (first ihrms business module)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-12

All objects in the ihrms schema. Leave requests reference employees by
soft employee_id (no FK into public). Seeds the standard India leave
types (EL/CL/SL) from the prototype config; richer rules kept in a JSONB
column so the prototype's full policy shape is preserved for later.
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table ihrms.leave_type (
            id              uuid primary key default gen_random_uuid(),
            tenant_id       text not null default 'atvantiq',
            key             text not null,
            code            text not null,
            label           text not null,
            color           text not null default 'indigo',
            description     text,
            is_paid         boolean not null default true,
            consumes_balance boolean not null default true,
            -- accrual: 'annual_upfront' | 'monthly' | 'event_based'
            accrual_method  text not null default 'annual_upfront',
            annual_entitlement numeric(6,2) not null default 0,
            monthly_rate    numeric(5,2) not null default 0,
            -- application rules (common ones promoted to columns)
            min_advance_notice_days int not null default 0,
            max_consecutive_days int,
            half_day_allowed boolean not null default true,
            requires_doc    boolean not null default false,
            allow_probationers boolean not null default true,
            gender_eligibility text not null default 'all',  -- all|male|female
            carry_forward_enabled boolean not null default false,
            carry_forward_max numeric(6,2) not null default 0,
            rules           jsonb not null default '{}',      -- full prototype policy
            show_in_ess     boolean not null default true,
            sort_order      int not null default 0,
            is_active       boolean not null default true,
            created_at      timestamptz not null default now(),
            updated_at      timestamptz not null default now()
        )
    """)
    op.execute("create unique index ux_leave_type_key on ihrms.leave_type (tenant_id, key)")
    op.execute("alter table ihrms.leave_type enable row level security")

    op.execute("""
        create table ihrms.leave_balance (
            id              uuid primary key default gen_random_uuid(),
            tenant_id       text not null default 'atvantiq',
            employee_id     bigint not null,
            leave_type_id   uuid not null references ihrms.leave_type(id),
            period_year     int not null,            -- leave year (calendar for now)
            entitled        numeric(6,2) not null default 0,
            accrued         numeric(6,2) not null default 0,
            carried_forward numeric(6,2) not null default 0,
            used            numeric(6,2) not null default 0,
            pending         numeric(6,2) not null default 0,
            updated_at      timestamptz not null default now(),
            unique (tenant_id, employee_id, leave_type_id, period_year)
        )
    """)
    op.execute("alter table ihrms.leave_balance enable row level security")

    op.execute("""
        create table ihrms.leave_request (
            id              uuid primary key default gen_random_uuid(),
            tenant_id       text not null default 'atvantiq',
            employee_id     bigint not null,
            leave_type_id   uuid not null references ihrms.leave_type(id),
            start_date      date not null,
            end_date        date not null,
            half_day        boolean not null default false,
            days            numeric(5,1) not null,   -- working days, halves allowed
            reason          text,
            status          text not null default 'pending'
                            check (status in ('pending','approved','rejected','cancelled')),
            applied_by      bigint not null,         -- self or HR (apply on behalf)
            approver_id     bigint,
            decision_note   text,
            decided_at      timestamptz,
            created_at      timestamptz not null default now(),
            updated_at      timestamptz not null default now()
        )
    """)
    op.execute("create index ix_leave_request_emp on ihrms.leave_request (employee_id, status)")
    op.execute("create index ix_leave_request_status on ihrms.leave_request (tenant_id, status)")
    op.execute("alter table ihrms.leave_request enable row level security")

    # Seed standard India leave types (from prototype LEAVE_TYPES_CONFIG)
    op.execute("""
        insert into ihrms.leave_type
          (key, code, label, color, description, accrual_method, annual_entitlement,
           monthly_rate, min_advance_notice_days, max_consecutive_days, half_day_allowed,
           requires_doc, allow_probationers, gender_eligibility, carry_forward_enabled,
           carry_forward_max, sort_order)
        values
          ('el','EL','Earned Leave','indigo',
           'Annual leave for planned absences, vacations, personal time off',
           'monthly', 18, 1.5, 7, 15, true, false, false, 'all', true, 30, 1),
          ('cl','CL','Casual Leave','amber',
           'Short-term leave for unforeseen personal needs, emergencies',
           'annual_upfront', 7, 0, 0, 3, true, false, true, 'all', false, 0, 2),
          ('sl','SL','Sick Leave','rose',
           'For illness or medical reasons; medical certificate for extended absence',
           'annual_upfront', 7, 0, 0, 30, true, false, true, 'all', false, 0, 3)
    """)


def downgrade() -> None:
    op.execute("drop table if exists ihrms.leave_request")
    op.execute("drop table if exists ihrms.leave_balance")
    op.execute("drop table if exists ihrms.leave_type")
