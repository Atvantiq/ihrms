# RLS enforcement — app-role cutover runbook

> **Status: DONE on the dev DB (2026-06-13).** The `ihrms_app` role exists with
> the least-privilege grants below, `v_employee` is `security_invoker`, and the
> app's `DATABASE_URL` points at `ihrms_app`. RLS is enforced (verified:
> fail-closed without tenant, isolated across tenants, all endpoints pass).
> **Migrations still run as the owner** (`postgres`) — `ihrms_app` has no DDL
> rights and is subject to RLS, so run Alembic with the superuser `DATABASE_URL`,
> not the app one. The steps below are retained for staging/production cutover.

## Why this is needed

Migration `0006` adds tenant-isolation RLS policies + `FORCE ROW LEVEL SECURITY`
on all `ihrms.*` tenant tables, and `core/db.get_session` sets
`app.tenant_id` on every session. **But RLS is not yet enforced in practice**,
because the app currently connects through the Supabase pooler as `postgres`,
which has the `BYPASSRLS` attribute (and is the table owner). `FORCE` only
subjects the *owner*; a `BYPASSRLS`/superuser role bypasses policies entirely.

Proven on 2026-06-13: connecting as `postgres` with no `app.tenant_id`, or with
a wrong tenant, still returns all rows.

**Real tenant isolation requires the app to connect as a dedicated,
non-privileged role.** This is a deliberate security/ops change on the shared
ONAQT database, so it is documented here rather than auto-applied.

## Cutover steps (run by an authorized operator)

1. **Create the app role** (one-time), as a superuser:

   ```sql
   create role ihrms_app with login password '<STRONG_SECRET>'
     nosuperuser nobypassrls noinherit;
   ```

2. **Grant least-privilege access** — only what the app actually touches:

   ```sql
   grant usage on schema ihrms, public, auth to ihrms_app;

   -- iHRMS owns these: full DML + future tables
   grant select, insert, update, delete on all tables in schema ihrms to ihrms_app;
   alter default privileges in schema ihrms
     grant select, insert, update, delete on tables to ihrms_app;
   grant usage on all sequences in schema ihrms to ihrms_app;

   -- ONAQT (shared) — exactly the tables/ops the app uses, nothing more
   grant select, insert, update on public.employees       to ihrms_app;
   grant select, insert, update on public.job_details      to ihrms_app;
   grant select, insert, update on public.employee_details to ihrms_app;
   grant select                 on public.addresses        to ihrms_app;
   grant select, insert         on public.global_ids       to ihrms_app;

   ```

   The app deliberately does **not** access the Supabase-owned `auth` schema
   (it resolves emails via `public.employees`), so no grant there is needed.

3. **Make `ihrms.v_employee` honour RLS** (Postgres 15+): so the view's
   joins to `ihrms.user_account` are tenant-scoped for the caller, recreate it
   `with (security_invoker = true)`. Otherwise the view runs as its owner
   (postgres) and bypasses RLS for the underlying ihrms joins.

4. **Point the app at the new role** — update `DATABASE_URL`:

   ```
   postgresql://ihrms_app.emckffbgrxwifwymhikv:<STRONG_SECRET>@aws-1-ap-south-1.pooler.supabase.com:5432/postgres
   ```

5. **Verify** (must all hold):
   - `select count(*) from ihrms.leave_type` with no `app.tenant_id` → `0` (fail-closed)
   - with `set_config('app.tenant_id','atvantiq',false)` → real counts
   - every API endpoint still works (smoke test: directory, profile, add/edit,
     org masters, leave apply/approve, audit) — a missing grant surfaces as a
     `permission denied` and must be granted before go-live.

6. **Secret management**: store `<STRONG_SECRET>` in Vault/secret manager, not
   in git. Rotate the `postgres` password too (it has been used during dev).

## Multi-tenant note

`get_session` currently sets `app.tenant_id` from `settings.tenant_id`
(single tenant `atvantiq`). When onboarding multiple tenants, derive it from
the authenticated principal's tenant instead, so each request is scoped to the
caller's tenant. The RLS policies already enforce it.
