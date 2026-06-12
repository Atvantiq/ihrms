# 24 — ONAQT Shared-Database Integration

**Context.** Atvantiq runs ONAQT (dev.onaqt.com) — a live field-workforce platform (attendance, multi-circle teams) whose employee master lives in a Supabase Postgres (project `emckffbgrxwifwymhikv`, ap-south-1 Mumbai, micro compute). iHRMS will **share this database**: reuse the existing employee tables as the single source of truth, add everything else in its own schema, and never alter what production depends on. Later, iHRMS becomes the employee master and syncs outward via APIs.

> Inspected live on 2026-06-12 (read-only) — Alembic rev `a119d41daef6`, 14 tables, ~43 employees, 43 auth users.

## 24.1 Existing schema (public) — DO NOT MODIFY

### Employee cluster (shared with iHRMS)
| Table | Rows | Purpose | Key facts |
|---|---|---|---|
| `employees` | ~43 | Employee master | PK `id` uuid; **business key `employee_id` bigint UNIQUE** (all FKs point here); `employee_code`, `email` (links to auth), names, `short_name`, `phone`, `date_of_birth`, `gender`, `is_active` smallint |
| `employee_details` | ~1 | Personal extras | `fathers_name`, `mothers_name`, `marital_status`, `spouse_name`, `alternate_phone`, `pan_no`, `adhar_no` — mostly unpopulated |
| `addresses` | ~2 | Employee addresses | free-form fields + `type`; FK → employees.employee_id |
| `job_details` | ~42 | Job assignment | `designation`, `circle_id` bigint (no local circles table), `branch`, `department`, `division` — **all free text**, `reporting_manager` FK → employees.employee_id, `date_of_joining/leaving`, `is_active` |
| `employee_official_location` | ~42 | Geo-fence/site pin | lat/long + is_active |
| `notification_tokens` | ~4 | Push tokens | device_type + token |
| `global_ids` | ~4152 | **ID registry** | single `id` bigint column; 12-digit random IDs; `employee_id` and `circle_id` values are drawn from it |

### Vendor cluster (ONAQT-only for now; future hook for iHRMS Finance/Purchases)
`vendors` (Zoho Books-synced: zoho_contact_id, PAN/GST/MSME/TDS, payment terms, balances), `vendor_addresses`, `vendor_bank_accounts`, `vendor_contact_persons`, `vendor_zoho_sync_logs`, `zoho_credentials` (Zoho OAuth refresh tokens).

### Auth
Supabase Auth (`auth.users`, 43 users). **No FK between employees and auth.users — linkage is by email** (39/43 match today; 4 unmatched = cleanup item). MFA/OTP capable (factor types totp/webauthn/phone).

### Platform observations
- **No RLS on any public table** — isolation is app-level only today.
- Existing backend is **Python + Alembic** (`alembic_version` present) — consistent with our FastAPI choice; iHRMS must use a **separate Alembic version table** (`ihrms.alembic_version_ihrms`) so the two migration histories never collide.
- Conventions to respect when touching shared rows: `is_active` smallint (0/1, not boolean), `created_at/updated_at` timestamptz defaults, uuid PK + bigint business key pattern.
- Data quality (job_details): department/division/branch are uncontrolled free text with duplicates/typos (`TELECOM/Telecome/TELECOME`, `it/IT`). Only 4 circle_ids in use; circles master lives outside this DB.

## 24.2 Integration rules (the contract that protects production)

1. **Never** rename/drop/retype anything in `public`; no NOT NULL or new constraints on existing tables; no triggers on existing tables.
2. **All iHRMS objects live in schema `ihrms`** — tables, views, functions, its own Alembic history.
3. **Soft references only**: iHRMS tables store `employee_id bigint` but declare **no FK into `public`** (and none from `public` into `ihrms`), so neither system can block the other. Integrity is enforced app-side + a nightly orphan-check job.
4. **Shared writes are additive and convention-following**: when iHRMS creates an employee it inserts `global_ids` → `employees` → `job_details` exactly as ONAQT does (same ID scheme, same smallint flags), inside one transaction.
5. **Reads via views**: `ihrms.v_employee` joins `public.employees + job_details + employee_details + addresses` into the canonical iHRMS employee shape; app code never queries `public` directly.
6. New optional columns on existing tables are allowed only as a last resort, nullable, and coordinated with the ONAQT team.

## 24.3 What iHRMS reuses vs adds

**Reuses (source of truth stays in `public`):** identity & contact (employees), personal details (employee_details — iHRMS will start populating PAN/Aadhaar properly), addresses, job assignment & reporting line (job_details), auth (Supabase Auth shared → **one login for ONAQT + iHRMS**, matched by verified email).

**Adds in `ihrms` (everything else from the blueprint):** org masters (departments/designations/grades/locations as *governed* masters — see mapping below), employment events, documents, leave (types/policies/balances/requests), attendance summaries & regularisation, payroll (salary structures, runs, payslips, statutory), expenses/assets/recoveries, TA (requisitions→onboarding), performance/goals, announcements, audit log, settings. Multi-tenant columns (`tenant_id`) stay in the schema per the blueprint, with this deployment running as tenant `atvantiq`; RLS is enabled on `ihrms.*` from day one.

**Master-data cleanup (required before payroll):** create `ihrms.departments/divisions/branches/designations` masters + mapping table from the free-text values in `job_details`; new writes go through masters while `job_details` keeps receiving the text value (dual-write) until ONAQT migrates to the API.

## 24.4 Auth bridge

`ihrms.user_account` maps `auth.users.id (uuid)` ↔ `employee_id (bigint)` + iHRMS roles/persona. Login = Supabase Auth (existing OTP/password flows keep working for ONAQT). iHRMS FastAPI validates the Supabase JWT, resolves employee + roles via this table. The 4 unmatched auth users get reconciled during go-live.

## 24.5 Phasing

| Phase | State |
|---|---|
| **P1 (now)** | Shared DB. iHRMS reads/writes `public` employee cluster per §24.2; everything new in `ihrms`. |
| **P2** | iHRMS becomes employee master: ONAQT consumes employee CRUD via iHRMS APIs; direct `public` writes from ONAQT stop; dual-write ends. |
| **P3 (if scale demands)** | Split: iHRMS moves to its own Postgres (schema already self-contained → `pg_dump -n ihrms`); ONAQT keeps a synced read model via webhooks/API. |

**Watch-outs:** micro compute (t4g.micro, 60-conn cap) is fine for ~43 employees but payroll runs + ONAQT peak attendance may contend — use PgBouncer pooling (already via Supabase pooler), keep iHRMS batch jobs off ONAQT's peak hours, upgrade compute before payroll go-live. Connection from IPv4 networks must use the **session pooler** (`aws-1-ap-south-1.pooler.supabase.com`); the direct host is IPv6-only.
