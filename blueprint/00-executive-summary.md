# 0 — Executive Summary & System Overview

## 0.1 What was analysed

A single-file HTML prototype (`atvantiq-people-prototype_2.html`, 28,238 lines) that simulates a complete enterprise iHRMS entirely in the browser. It contains:

- **41 distinct screens** registered in a `SCREENS{}` dispatch table, plus dozens of sub-tabs and modal flows.
- **~200 JavaScript data structures** (`const`/`let` object & array literals) that encode the full domain model — these are the Rosetta Stone for reverse-engineering entities.
- **A 7-persona company-side role model** (`employee, manager, it, finance, hr, reviewer, super`) with feature-gated navigation (`personaHas()`).
- **A 9-role platform-side role model** (`SA_ROLES`: owner, ops, release, compliance, billing, security, ai, support, auditor).
- A **command palette**, AI inbox, workflow routing engine, SLA model, and an entire Super-Admin SaaS control plane.

The prototype is **front-end only**: no backend, no persistence (in-memory mutation), no authentication, actions are toast notifications, and validation is largely absent. The *design intent* is enterprise-complete; the *implementation* is a simulation. This blueprint converts intent into a buildable specification.

## 0.2 The product in one diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                       CONTROL PLANE (Super-Admin)                      │
│  Tenants · Plans/Entitlements · Billing(PEPM) · Releases/Flags ·       │
│  Compliance Packs · Statutory Master · Security/SSO/Impersonation ·    │
│  AI Governance · Integrations · Observability · Data Governance · Dev  │
└───────────────▲───────────────────────────────────────▲───────────────┘
                │ provisions / governs / meters          │ statutory & compliance packs
┌───────────────┴───────────────────────────────────────┴───────────────┐
│                    TENANT PLANE (Company HRMS)  — per tenant            │
│                                                                        │
│   HIRE ──────► ONBOARD ──────► MANAGE ──────► PAY ──────► GROW ──► EXIT │
│  ┌────────┐  ┌──────────┐  ┌────────────┐ ┌────────┐ ┌────────┐ ┌─────┐ │
│  │Talent  │  │Onboarding│  │Core HR     │ │Payroll │ │Perf &  │ │Exit │ │
│  │Acquisi-│  │+ BGV +   │  │Directory   │ │Statutory│ │Growth  │ │+ F&F│ │
│  │tion    │  │Probation │  │Profile/ESS │ │Tax/Adv │ │PIP/9box│ │     │ │
│  └────────┘  └──────────┘  │Time/Attend │ │Assets  │ └────────┘ └─────┘ │
│                            │Leave/OOD   │ │Finance │                    │
│                            │Timesheet   │ └────────┘                    │
│                            │Helpdesk    │                               │
│                            └────────────┘                               │
│   Cross-cutting: Workflow/Approval Engine · Notifications · Reports ·   │
│                  Pulse AI · Audit · Document mgmt · RBAC/Delegation     │
└────────────────────────────────────────────────────────────────────────┘
```

## 0.3 Functional domains discovered (12)

| # | Domain | Screens (key) | Single-sentence purpose |
|---|--------|---------------|--------------------------|
| 1 | **Core HR & ESS** | dashboard, directory, profile, ess, tasks | Employee master, self-service, unified approvals inbox. |
| 2 | **Talent Acquisition** | ta-planning…ta-analytics, candidate-portal | Req → source → interview → offer → BGV → onboard → confirm. |
| 3 | **Time & Attendance** | (T&A workspace), profile/ESS time tabs | Capture punches from many sources, shifts, regularization, OT. |
| 4 | **Leave & OOD** | leave | Leave types/balances/requests, comp-off, OOD/WFH duty pre-approval. |
| 5 | **Timesheet & Project time** | timesheet | Client/project/task time, billing, utilization, cost centers. |
| 6 | **Payroll & Statutory** | payroll | Salary structures, run engine, PF/ESI/PT/TDS, bank file. |
| 7 | **Tax & Declarations** | payroll (tax tab) | Old/new regime, investment proofs, FY declarations. |
| 8 | **Assets & Access** | finance-asset, asset registry | Asset lifecycle, requests, licenses, access provisioning, depreciation. |
| 9 | **Finance ops** | finance-purchases, finance-recoveries | Purchase approvals, cross-module recoveries, cost-center budgets. |
| 10 | **Performance & Growth** | performance suite | Goals/OKRs, reviews, calibration, 9-box, PIP, succession, increments. |
| 11 | **Exit & F&F** | exit pipeline | Resignation → clearance → KT → full-and-final settlement. |
| 12 | **Platform / SaaS Ops** | all super-* | Multi-tenancy, billing, governance, security, observability. |
| + | **Cross-cutting services** | (engine) | Workflow/approvals, notifications, reports, Pulse AI, audit, docs. |

## 0.4 The five system-defining design decisions (observed in code)

1. **Single identity from candidate to employee.** `TA_CANDIDATES` carry an `employee_id`; `TA_JOINED` marks the Day-1 crossing; the candidate portal and ESS share one login. *Implication:* the Person/Identity entity is foundational and spans recruiting + HR.
2. **A generic workflow/approval engine, not hard-coded approvals.** `WORKFLOW_ROUTING` defines ordered `steps[]` with role resolution (org-chart auto / designated pool / specific person), `any`/`all` modes, amount-gated escalation, and an SLA model. *Implication:* build one workflow service; every module's approvals are configurations of it.
3. **A unified multi-hat task inbox.** `tasks` aggregates "awaiting me / by me / all / urgent" across every module. *Implication:* approvals are first-class cross-module objects.
4. **Per-tenant module entitlement.** The control plane gates 15 modules per tenant by plan. *Implication:* every feature must be feature-flag/entitlement gated at the tenant boundary.
5. **Compliance & statutory as governed, versioned, published artifacts.** The control plane ships "compliance packs" and a statutory rate master to tenants through an 8-state publish workflow. *Implication:* statutory rules are data, centrally curated and versioned — not code.

## 0.5 Headline gaps (full list in `12-gap-analysis.md`)

The prototype is UI-complete but **engine-empty**. The biggest build-side gaps, common across modules:

- **No persistence, no real identity/auth, no RBAC enforcement** — everything is client-side.
- **No notification/reminder/SLA-clock engine** — channels and intervals are declared but inert.
- **No computation engines** — payroll TDS, leave accrual, depreciation schedules, attendance reconciliation→LOP, F&F math are partially modeled but not executable.
- **No audit immutability** — audit logs are mutable in-memory arrays.
- **No document generation** — payslips, Form 16, offer letters, relieving letters are referenced but not produced.
- **No statutory filing artifacts** — PF ECR, ESIC, PT challans, 24Q/Form 16 are named but not generated.
- **No validation layer** — PAN/Aadhaar/IFSC/email, balance caps, blackout/notice rules unenforced.

These gaps define the bulk of the real engineering work; the UI is the easy 30%.

## 0.6 How to use this blueprint to start building tomorrow

1. **Foundation team** builds Identity, Tenancy, RBAC, Workflow engine, Notifications, Audit, Document service (see roadmap M0–M1).
2. **Module teams** can then build in dependency order (see `14-dependency-map.md`): Core HR → Time/Leave → Payroll → TA → Performance → Exit, each consuming foundation services.
3. **Platform team** builds the control plane in parallel (it depends only on Identity/Tenancy/Billing primitives).

The remaining documents specify each of these precisely.
