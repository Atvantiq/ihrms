# 15 — Implementation Roadmap (Step 7)

**Dependency-driven, not generic.** The milestone count, scope, and sequence are derived directly from `14-dependency-map.md`. The governing logic: *build the foundation once, build the system of record next, then build feeders before sinks (Payroll, Exit are sinks), and run the control plane on a parallel track.*

The number of milestones (**8**) falls out of the 6 dependency layers plus a foundation milestone plus a hardening/GA milestone. Two parallel tracks run throughout: **Track A (Tenant HRMS)** and **Track B (Control Plane)**.

---

## Milestone 0 — Platform Foundation (Track A + B shared)
**Why first:** Every module depends on these; nothing real can be built without persistence, identity, and the workflow/notification/audit services. Retrofitting audit/RBAC later is a compliance and rework disaster.

**Scope (Track A foundation):**
- Multi-tenant data isolation + region pinning; tenant provisioning primitive.
- Identity & Auth: password, **SSO/SAML/OIDC, MFA**, session management.
- RBAC & scopes (role → capability → scope), policy enforcement point.
- **Workflow/Approval engine** (routing, modes, amount-gating, SLA model, snapshotting, delegation).
- **Notification engine** (email/SMS/in-app/push; templates; preferences).
- **Audit service** (append-only, hash-chained, immutable).
- **Document service** (templating, PDF gen, storage, e-sign integration) + object storage + AV scan.
- Job/queue/scheduler; search index; API gateway; feature-flag/entitlement client.
- Validation framework (PAN/Aadhaar/IFSC/GST/email + rule DSL).

**Track B (parallel):** Tenant entity & lifecycle, Plans/Entitlements, basic Billing skeleton, platform Identity/roles.

**Exit criteria:** A tenant can be provisioned; a user can log in via SSO+MFA; a generic request can be submitted, routed, SLA-tracked, notified, audited, and approved end-to-end; a templated PDF can be generated and e-signed.

---

## Milestone 1 — Core HR System of Record (Track A)
**Why now:** The single-identity Employee Master is the spine every later module reads; TA later *writes* to it.

**Scope:** Employee/Person master (full HRIS fields, effective-dated job & comp history), Org structure engine (department/designation/band/grade, reporting & skip-level, vacancies/matrix), Directory (search, filters, bulk ops, letters), Employee 360 Profile (all tabs), ESS shell (9 tabs scaffolded), Helpdesk/Requests (19 types on the workflow engine), Consent & data-retention lifecycle (DPDP).

**Exit criteria:** Employees can be created/imported, placed in org, viewed in directory/profile, and can self-serve generic requests via ESS.

---

## Milestone 2 — Time, Attendance, Leave & Timesheet (Track A)
**Why now:** These are the operational feeders that Payroll consumes; they depend only on Core HR + foundation. Building them before Payroll means Payroll has real inputs.

**Scope:**
- Attendance capture (multi-source, allowlist, reconciliation), shifts/rotations, holidays/locations, regularization, OT, L1/L2 day approval + auto-finalize, overrides.
- **Leave accrual engine**, leave types/balances/requests, comp-off, OOD/WFH (auto-attendance), validations (balance, blackout, sandwich, notice).
- Timesheet (entry, projects/clients/tasks, approval, billing rollups, utilization), cost centers + tiered approval.
- Device/geofence integration adapters (biometric, GPS+selfie).

**Exit criteria:** A month of attendance + approved leave + timesheets produces clean, query-able LOP/OT/encashment/billing inputs.

---

## Milestone 3 — Payroll, Statutory, Tax & Bank (Track A) ⟂ Track B statutory master
**Why now:** Payroll is a *sink* — it needs Core HR (comp), Time/Leave (LOP/OT/encash), Advances, and the **statutory rate master** (built on Track B). All exist by now.

**Scope:**
- Salary component & structure engine (all calc types, balancing, tax treatment), pay groups.
- **TDS computation engine** (both regimes, rebate/surcharge/cess, projection), tax declarations + proof verification.
- Payroll run state machine (draft→preview→approved→bankfile→paid), maker-checker, holds, variance.
- Statutory: PF/ESI/PT/gratuity compute; **ECR/ESIC/PT challan**, **24Q/Form 16/12BA** generation; establishment-level monthly consolidation.
- **Payslip PDF**, bank file + NEFT/H2H + UTR reconciliation, **GL/journal posting**, arrears/retro.
- Advances/loans lifecycle + payroll deduction.

**Track B dependency:** Statutory rate master + compliance-pack publish pipeline must be live before this milestone's compute work.

**Exit criteria:** Run payroll for a tenant end-to-end: correct net pay, payslips, bank file, statutory filings, GL entries.

---

## Milestone 4 — Talent Acquisition & Onboarding (Track A)
**Why here (not earlier):** TA depends on the Employee Master (single identity) and Document/Workflow/Assets/Access to issue a real employee on Day-1. Placing it after Core HR + foundation lets onboarding actually provision a working employee (profile, assets, access, payroll structure).

**Scope:** Workforce planning (+headcount writeback), requisitions (with reject/return), ATS/recruiting pipeline, sourcing + job-board integrations, interviews + scheduling + video, offers (versioning/e-sign), **BGV (vendor APIs + consent/retention)**, onboarding templates (provisioning assets/access/structure), candidate portal → ESS handoff, probation hard-gate, TA analytics, dedup.

**Exit criteria:** A candidate moves req→offer→BGV→Day-1 and becomes a fully provisioned employee with no re-entry.

---

## Milestone 5 — Performance & Growth (Track A)
**Why here:** Depends on Employee/Org and integrates with Payroll (increment bridge), both live by now.

**Scope:** Goals/OKRs (+ real cascade/roll-up), check-ins, feedback/recognition/360, review cycle state machine, calibration + 9-box (+ enforced normalization option), promotions/increments (+ comp-band/budget guardrails) → payroll bridge, PIP (+ exit linkage), succession, dev/career paths, mentorship, competency framework, performance analytics/history.

**Exit criteria:** Run a full review cycle that publishes ratings and pushes approved increments into payroll.

---

## Milestone 6 — Exit & Full-and-Final (Track A)
**Why last among HR modules:** F&F is the final integrator — it consumes Payroll, Assets, Leave, Performance, Advances.

**Scope:** Exit pipeline, KT, clearance (auto-deprovision assets/access via SCIM), **F&F computation engine** (gratuity, leave encashment, notice recovery, tax), recoveries aggregation, exit document generation (relieving/experience/no-dues/service), final payroll + UTR.

**Exit criteria:** A resignation flows to a computed, approved, paid F&F with all documents and access revoked.

---

## Milestone 7 — Cross-cutting Intelligence, Hardening & GA
**Scope:** Reports/analytics warehouse + 35 prebuilt + custom builder + scheduling; Pulse AI (attrition, insights) on real data; dashboards; full notification preferences/digests; performance/load testing to scale targets; security pen-test; DR drills; data-migration/import tooling with validation/rollback; observability in tenant app; documentation & runbooks.

**Exit criteria:** Meets all NFRs (scale, availability, security, DR); GA-ready.

---

## Track B — Control Plane (parallel, M0→M7)

Sequenced by its own light dependencies (Tenancy/Identity/Billing first):

| TB-Milestone | Scope | Aligns with |
|--------------|-------|-------------|
| TB0 | Tenant lifecycle & provisioning, platform identity/roles, plans/entitlements | M0 |
| TB1 | Billing & metering (PEPM), invoices, revenue | M0–M1 |
| TB2 | **Statutory rate master + compliance-pack publish pipeline** | before M3 (gates Payroll) |
| TB3 | Releases/flags/rings/rollouts, templates, announcements | M1–M2 |
| TB4 | Security (SSO/MFA admin, impersonation, secrets, masking), AI governance | M2–M4 |
| TB5 | Integrations hub, developer/API/webhooks | M4 |
| TB6 | Observability, data governance (retention/residency/legal-hold/DR), support/RCA | M5–M7 |

**Hard cross-track gate:** TB2 (statutory master) must complete before M3 (Payroll compute).

---

## Roadmap rationale summary

| Decision | Justification (from dependency analysis) |
|----------|------------------------------------------|
| 8 milestones | 6 dependency layers + 1 foundation + 1 hardening. |
| Foundation first | All modules depend on Layer 0; audit/RBAC must be native. |
| Core HR before everything | Single-identity Employee Master is the spine. |
| Time/Leave before Payroll | Payroll is a sink needing their outputs. |
| Statutory master (TB2) gates Payroll | Payroll compute needs centrally-published rates. |
| TA after Core HR | Onboarding must issue a fully-provisioned employee. |
| Exit last | F&F integrates Payroll+Assets+Leave+Performance. |
| Control plane parallel | Decoupled from HR internals; separate team. |

## Team topology (suggested, enables parallelism)

- **Platform/Foundation team** → M0, shared services (owns workflow/notification/audit/document/identity).
- **Core HR team** → M1, then Performance (M5).
- **Time & Pay team** → M2 + M3 (the heaviest, statutory-critical track).
- **TA team** → M4 (+ candidate portal).
- **Exit/Finance team** → Assets (M2 slice) + Exit/F&F (M6).
- **Control-plane team** → Track B throughout.
- **Data/Reporting team** → Reports/Pulse warehouse (M7, starting early).
