-- Minimal ONAQT `public` schema for integration tests.
-- Mirrors the columns the iHRMS app reads/writes (see blueprint doc 24);
-- not the full ONAQT schema. Lets ihrms migrations + app queries run against
-- an ephemeral Postgres without touching the real shared database.

create schema if not exists public;

-- Minimal stand-in for Supabase Auth (migration 0002 backfills from it).
create schema if not exists auth;
create table if not exists auth.users (
    id    uuid primary key,
    email varchar
);

create table if not exists public.global_ids (
    id bigint primary key
);

create table if not exists public.employees (
    id            uuid primary key default gen_random_uuid(),
    employee_id   bigint not null unique,
    employee_code varchar not null,
    email         varchar not null,
    first_name    varchar not null,
    middle_name   varchar,
    last_name     varchar,
    short_name    varchar not null,
    phone         varchar not null,
    date_of_birth date,
    gender        varchar,
    is_active     smallint not null default 1,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz default now()
);

create table if not exists public.job_details (
    id                uuid primary key default gen_random_uuid(),
    employee_id       bigint not null,
    designation       varchar not null,
    circle_id         bigint not null,
    branch            varchar not null,
    department        varchar not null,
    division          varchar not null,
    reporting_manager bigint,
    date_of_joining   date not null,
    date_of_leaving   date,
    is_active         smallint not null default 1,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz default now()
);

create table if not exists public.employee_details (
    id             uuid primary key default gen_random_uuid(),
    employee_id    bigint not null,
    fathers_name   varchar,
    mothers_name   varchar,
    marital_status varchar,
    spouse_name    varchar,
    alternate_phone varchar,
    pan_no         varchar,
    adhar_no       varchar,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz default now()
);

create table if not exists public.addresses (
    id          uuid primary key default gen_random_uuid(),
    employee_id bigint not null,
    city        varchar,
    state       varchar,
    type        varchar,
    created_at  timestamptz not null default now()
);
