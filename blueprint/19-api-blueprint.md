# 19 — API Blueprint

## 19.1 API principles

- **REST + JSON** as the primary contract (resource-oriented), **OpenAPI 3.1** spec-first. Optional **GraphQL** read layer for composite dashboards/ESS to avoid over-fetching.
- **Versioned** under `/v1`; additive, backward-compatible evolution; deprecation policy with sunset headers.
- **Tenant context** from the auth token (`tenant_id` claim); never a path/query param the client controls.
- **Entitlement-gated** at the gateway: a call to a module the tenant isn't entitled to → `403 module_not_entitled`.
- **Idempotency** on all unsafe POSTs via `Idempotency-Key` header.
- **Pagination** (cursor-based), **filtering**, **sorting**, **sparse fieldsets** standardised.
- **RFC 7807** problem+json errors.
- **Webhooks** for async/outbound events; **public API + sandbox** (the control plane already models API keys, webhooks, 9 event types, sandbox, docs).

## 19.2 Auth

```
POST /v1/auth/login                      password (fallback)
GET  /v1/auth/sso/{provider}             OIDC/SAML redirect
POST /v1/auth/mfa/verify
POST /v1/auth/refresh
POST /v1/auth/logout
SCIM 2.0:  /scim/v2/Users, /scim/v2/Groups   (enterprise provisioning)
```
Bearer JWT (short-lived) + refresh; tokens carry `tenant_id`, `user_id`, `roles`, `scopes`. Service-to-service via mTLS + scoped tokens.

## 19.3 Resource map (tenant plane) — representative endpoints

### Identity / RBAC / Workflow (foundation)
```
GET    /v1/me                                       profile + roles + entitlements
CRUD   /v1/roles  /v1/roles/{id}/capabilities
CRUD   /v1/delegations
GET    /v1/tasks?bucket=awaiting|by_me|all|urgent   unified inbox
POST   /v1/requests                                 create any request (type in body) → workflow
POST   /v1/workflow-instances/{id}/approve|reject|return|reassign
GET    /v1/workflow-instances/{id}                  status + routing + SLA
CRUD   /v1/workflow-defs  (admin: routing, SLA, channels)
GET    /v1/notifications  ·  POST /v1/notifications/{id}/read  ·  PUT /v1/notification-prefs
GET    /v1/audit-events?entity=&from=&to=           (read-only, immutable)
POST   /v1/documents:generate  ·  GET /v1/documents/{id}  ·  POST /v1/documents/{id}:sign
POST   /v1/consents  ·  GET /v1/consents
```

### Core HR
```
CRUD   /v1/employees                                + /v1/employees:import (bulk)
GET    /v1/employees/{id}  (profile 360, ?include=job,comp,documents,family,compliance)
PATCH  /v1/employees/{id}/job   (effective-dated)   PATCH .../comp
GET    /v1/directory?dept=&location=&q=             search/filter
CRUD   /v1/org/departments /designations /bands /grades /locations /establishments
POST   /v1/letters:generate                         offer/confirmation/etc.
```

### ESS (employee-scoped, self)
```
GET    /v1/ess/home  /ess/payslips  /ess/announcements
POST   /v1/ess/leave-requests  /ess/ood-requests  /ess/regularizations
POST   /v1/ess/claims  /ess/advances  /ess/profile-updates  /ess/declarations  /ess/asset-requests
GET    /v1/ess/requests                             my requests + status
```

### Talent Acquisition
```
CRUD   /v1/ta/headcount /requisitions /candidates /interviews /offers
POST   /v1/ta/requisitions/{id}:approve|reject
POST   /v1/ta/candidates/{id}:advance|reject       stage transition
POST   /v1/ta/offers/{id}:release|accept|decline   accept → triggers BGV
CRUD   /v1/ta/bgv-cases  ·  POST /v1/ta/bgv-cases/{id}:adjudicate
CRUD   /v1/ta/onboarding  ·  POST /v1/ta/onboarding/{id}/tasks/{tid}:complete
POST   /v1/ta/candidates/{id}:day1                  issues employee identity
GET    /v1/ta/analytics/funnel|sources|time-to-fill
Candidate portal (token-scoped): /v1/portal/me /portal/documents /portal/tasks /portal/esign
```

### Time / Attendance / Leave / Timesheet
```
POST   /v1/attendance/events                        device/mobile punch (geo+selfie)
GET    /v1/attendance/days?employee=&month=
POST   /v1/attendance/days/{id}:approve-l1|approve-l2|override
CRUD   /v1/regularizations  /ot-records
CRUD   /v1/leave/types /balances /requests
POST   /v1/leave/requests/{id}:approve|reject|cancel
CRUD   /v1/comp-off  /ood-requests
CRUD   /v1/timesheets  ·  POST /v1/timesheets/{id}:submit|approve|reopen
CRUD   /v1/projects /clients /tasks /cost-centers /rate-cards
```

### Payroll / Statutory / Tax
```
CRUD   /v1/payroll/components /structures /pay-groups
POST   /v1/payroll/runs                              create run
POST   /v1/payroll/runs/{id}:preview|approve|generate-bankfile|mark-paid
GET    /v1/payroll/runs/{id}/register
POST   /v1/payroll/runs/{id}/lines/{eid}:hold|release
CRUD   /v1/tax/declarations  ·  POST .../{id}:verify|lock
GET    /v1/tax/tds/{employee}?fy=
CRUD   /v1/advances  ·  POST /v1/advances/{id}:approve
POST   /v1/statutory/filings:generate?type=ecr|esic|pt|24q|form16
GET    /v1/payslips/{employee}/{month}              PDF
```

### Assets / Performance / Exit
```
CRUD   /v1/assets /asset-requests /licenses /access-profiles
POST   /v1/asset-requests/{id}:advance               stage transitions
CRUD   /v1/performance/cycles /goals /reviews /pips /increments
POST   /v1/performance/cycles/{id}:advance-stage
POST   /v1/performance/increments/{id}:push-to-payroll
CRUD   /v1/exit/cases  ·  POST /v1/exit/cases/{id}:advance
GET    /v1/exit/cases/{id}/fnf  ·  POST .../fnf:compute|approve|pay
POST   /v1/exit/cases/{id}/documents:generate
```

### Reports
```
GET    /v1/reports/catalog                           categories + 35 defs
POST   /v1/reports/{def}:run    (filters: period/dept/location)
GET    /v1/reports/runs/{id}                          status + artifact
CRUD   /v1/reports/schedules
POST   /v1/reports/custom                             builder + AI suggest
```

## 19.4 Control-plane API (platform operators + public)

```
CRUD   /v1/admin/tenants  ·  POST /v1/admin/tenants/{id}:provision|suspend|archive
CRUD   /v1/admin/plans /entitlements /modules
GET    /v1/admin/billing/invoices /metering /revenue
CRUD   /v1/admin/feature-flags  ·  POST .../{id}:rollout|kill
CRUD   /v1/admin/compliance-packs ·  POST .../{id}:advance (8-state publish)
CRUD   /v1/admin/statutory-rates
POST   /v1/admin/impersonations  ·  POST .../{id}:approve|start|end
CRUD   /v1/admin/ai-policies /integrations /announcements /templates
GET    /v1/admin/observability/jobs|queues|uptime|errors
CRUD   /v1/admin/data/retention|legal-hold|exports|backups|dr-tests

Public/dev: /v1/api-keys  /v1/webhooks  /v1/webhook-events  /v1/usage  /sandbox/*
```

## 19.5 Webhook events (outbound)

From the control plane's `SA_WEBHOOK_EVENTS` + tenant domain events:
```
tenant.created · tenant.plan.changed · tenant.feature.enabled · tenant.invoice.paid
tenant.compliance.acknowledged · tenant.integration.failed · tenant.ai.budget.threshold.reached
support.impersonation.started · audit.critical-action.logged
employee.hired · employee.terminated · offer.accepted · payroll.finalized
payslip.published · leave.approved · exit.initiated · fnf.paid
```
Delivery: signed (HMAC), retried with backoff, dead-lettered, replayable; `webhook_delivery` tracks status.

## 19.6 Standards & cross-cutting

| Concern | Standard |
|---------|----------|
| Spec | OpenAPI 3.1 (spec-first, generated clients) |
| Errors | RFC 7807 problem+json with `code`, `detail`, `field_errors` |
| Pagination | cursor: `?cursor=&limit=`; response `next_cursor` |
| Rate limiting | per-tenant + per-key token bucket; `429` + `Retry-After` |
| Idempotency | `Idempotency-Key` on POST |
| Concurrency | ETag / `If-Match` (optimistic lock via `version`) |
| Bulk | `:import` / `:export` async jobs returning a job handle |
| Long ops | `202 Accepted` + `Location` to a job resource (payroll, reports, filings) |
| Audit | every mutating call emits an `audit_event` |
| i18n | `Accept-Language`; money/date localised per tenant region |
