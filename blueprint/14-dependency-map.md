# 14 — Dependency Map (Step 6)

Dependency analysis **precedes** the roadmap (the roadmap is derived from it). Each module is classified as **Foundational** (others depend on it), **Dependent** (needs prior modules), or **Independent** (can build in isolation). Edges are "requires".

## 14.1 Layered dependency graph

```
LAYER 0 — PLATFORM FOUNDATION (no HR dependencies; everything depends on these)
  ┌─────────────────────────────────────────────────────────────────────┐
  │ Tenancy & Provisioning · Identity/Auth/SSO/MFA · RBAC & Scopes       │
  │ Workflow/Approval Engine · Notification Engine · Audit Service       │
  │ Document Service (gen+store+e-sign) · File/Object Storage            │
  │ Job/Queue/Scheduler · Search Index · API Gateway · Config/Flags      │
  └─────────────────────────────────────────────────────────────────────┘
                                    │
LAYER 1 — CORE HR SYSTEM OF RECORD (depends on Layer 0)
  ┌─────────────────────────────────────────────────────────────────────┐
  │ Employee/Person Master (single identity) · Org Structure (eff-dated) │
  │ Directory · Employee 360 Profile · ESS shell · Helpdesk/Requests     │
  └─────────────────────────────────────────────────────────────────────┘
                                    │
LAYER 2 — OPERATIONAL HR (depends on Layer 1)
  ┌──────────────┬──────────────┬──────────────┬────────────────────────┐
  │ Time &       │ Leave & OOD  │ Timesheet &  │ Assets & Access        │
  │ Attendance   │ (+ accrual)  │ Cost Centers │ (registry/req/access)  │
  └──────┬───────┴──────┬───────┴──────┬───────┴───────────┬────────────┘
         │              │              │                   │
LAYER 3 — PAYROLL & FINANCE (depends on Layer 2 inputs)
  ┌─────────────────────────────────────────────────────────────────────┐
  │ Salary Structures · Statutory/Tax engine · Payroll Run · Bank/Disb · │
  │ Advances/Loans · GL posting · Finance recoveries · Depreciation      │
  └─────────────────────────────────────────────────────────────────────┘
                                    │
LAYER 2′ — TALENT ACQUISITION (depends on Layer 1; feeds Layer 1)
  ┌─────────────────────────────────────────────────────────────────────┐
  │ Planning · Requisitions · ATS/Recruiting · Interviews · Offers ·     │
  │ BGV · Onboarding · Probation · Candidate Portal → (issues Employee)  │
  └─────────────────────────────────────────────────────────────────────┘
                                    │
LAYER 4 — TALENT MANAGEMENT (depends on Layer 1; integrates Layer 3)
  ┌─────────────────────────────────────────────────────────────────────┐
  │ Goals/OKRs · Feedback/360 · Review cycles · Calibration/9-box ·      │
  │ PIP · Succession · Increments → (feeds Payroll)                      │
  └─────────────────────────────────────────────────────────────────────┘
                                    │
LAYER 5 — LIFECYCLE CLOSE (depends on Layers 1–4)
  ┌─────────────────────────────────────────────────────────────────────┐
  │ Exit pipeline · KT · Clearance · F&F (consumes Payroll+Assets+Leave) │
  └─────────────────────────────────────────────────────────────────────┘

CROSS-CUTTING (consume all layers, build incrementally)
  Reports/Analytics · Pulse AI · Dashboards · Notifications preferences

CONTROL PLANE (parallel track — depends only on Tenancy/Identity/Billing)
  Tenants · Plans/Entitlements · Billing/Metering · Releases/Flags ·
  Compliance/Statutory packs · Security · AI gov · Observability · Data gov · Dev/API
```

## 14.2 Module dependency table

| Module | Type | Hard dependencies (must exist first) | Soft/consumes |
|--------|------|--------------------------------------|---------------|
| Tenancy & Provisioning | Foundational | — | — |
| Identity/Auth/SSO/MFA | Foundational | Tenancy | — |
| RBAC & Scopes | Foundational | Identity, Org (light) | — |
| Workflow/Approval Engine | Foundational | Identity, RBAC, Notifications | Org (resolution) |
| Notification Engine | Foundational | Identity | Templates |
| Audit Service | Foundational | Identity | — |
| Document Service | Foundational | Storage | Templates, e-sign |
| Job/Queue/Scheduler | Foundational | — | — |
| Search Index | Foundational | — | data sources |
| **Employee Master / Org** | Foundational (HR) | Layer 0 | TA (creates), Payroll/Perf (consumes) |
| Directory / Profile / ESS | Dependent | Employee Master, RBAC | all ops modules |
| Helpdesk/Requests | Dependent | Workflow, Employee | — |
| Time & Attendance | Dependent | Employee, Org, Workflow, Scheduler | Payroll (provides) |
| Leave & OOD | Dependent | Employee, Workflow, Scheduler (accrual) | Attendance, Payroll |
| Timesheet & Cost Centers | Dependent | Employee, Projects, Workflow | Billing, Payroll |
| Assets & Access | Dependent | Employee, Workflow | Exit (recoveries), IT provisioning |
| Salary Structures | Dependent | Employee, Statutory master | Payroll |
| Statutory/Tax engine | Dependent | Statutory rate master (control plane) | Payroll |
| **Payroll Run** | Dependent | Salary, Statutory/Tax, Attendance LOP, Leave, Advances, Increments | Bank, GL, Payslip, Filings |
| Bank/Disbursement | Dependent | Payroll, bank integration | reconciliation |
| Talent Acquisition | Dependent | Employee Master (single identity), Workflow, Document, BGV vendors | Onboarding→Employee |
| Onboarding | Dependent | TA, Workflow, Document, Assets, Access | issues Employee |
| Performance & Growth | Dependent | Employee, Org, Workflow | Payroll (increment) |
| Exit & F&F | Dependent | Employee, Payroll, Assets, Leave, Performance | Document, GL |
| Reports/Analytics | Cross-cutting | data from all modules | warehouse |
| Pulse AI | Cross-cutting | data + AI service | — |
| Control plane (each) | Parallel | Tenancy, Identity, Billing | governs tenant app |

## 14.3 Critical dependency rules (load-bearing, from design)

1. **Single identity is the spine.** Employee Master must exist before TA can "issue" employees and before any ops/payroll/perf module. TA *writes* to it; everyone else *reads* it.
2. **Workflow engine before any approval-bearing module.** Every operational module's approvals are configurations of it — build it once, first.
3. **Statutory rate master (control plane) before Payroll.** Payroll computation needs centrally-published rates; build the rate master + publish pipeline before the payroll engine.
4. **Attendance + Leave + Advances + Increments all feed Payroll.** Payroll is a *sink*; it cannot be correct until its upstream inputs exist. This makes Payroll a Layer-3 module, not an early win.
5. **Exit/F&F is the last integrator.** It consumes Payroll, Assets, Leave, Performance — it must come last among HR modules.
6. **Notifications + Audit are transverse.** Every transition emits both; build them as shared services early so modules wire into them from day one (retrofitting audit is expensive and compliance-risky).
7. **Control plane is decoupled** from HR module internals — it depends only on tenancy/identity/billing primitives, so it can be built by a separate team in parallel from M0.

## 14.4 Independent / parallelizable work

- **Control plane** (separate team, from M0).
- **Document service, Notification engine, Search** — independent shared services buildable in parallel within Layer 0.
- **Timesheet** has the lightest HR coupling (Projects/Clients are self-contained) — can progress in parallel once Employee Master exists.
- **Assets & Access** is largely independent of Payroll/TA — parallelizable in Layer 2.
- **Reports** can begin (schema + viewer) early and accrete data sources as modules land.

## 14.5 Modules that must NOT start before prerequisites

- ❌ Payroll Run before Salary + Statutory/Tax + Attendance/Leave/Advances inputs.
- ❌ Exit/F&F before Payroll + Assets + Leave.
- ❌ Any approval module before Workflow engine.
- ❌ Onboarding before Document + Assets + Access + Employee Master.
- ❌ Performance increment bridge before Payroll structures.
- ❌ Tenant app modules before Tenancy + Identity + RBAC.
