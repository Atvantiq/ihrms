# Atvantiq People (iHRMS) — Implementation Blueprint

> Reverse-engineered from `atvantiq-people-prototype_2.html` (28,238 lines, 41 screens, ~200 in-code data structures).
> This blueprint is the single source of truth for multiple development teams to begin implementation in parallel.

## What this product is

**Atvantiq People** is a **multi-tenant SaaS iHRMS** (Integrated Human Resource Management System) for the Indian market (with multi-country ambitions). It has two distinct planes:

1. **Tenant plane (Company app)** — the HRMS used by an employer's employees, managers, HR, finance and IT. Covers the full employee lifecycle: *Hire → Onboard → Manage → Pay → Grow → Exit.*
2. **Control plane (Super-Admin / SaaS operator)** — the platform-operator console that provisions tenants, governs releases, billing, compliance packs, security, AI, observability and data governance.

## Document map

| # | Deliverable | File |
|---|-------------|------|
| — | This index | `README.md` |
| 0 | Executive summary & system overview | `00-executive-summary.md` |
| — | **Module specs (Step 1 audit + Step 2 features)** | `modules/` |
| 1 | Core HR, ESS & platform plumbing | `modules/01-core-hr-ess.md` |
| 2 | Talent Acquisition, Onboarding & BGV | `modules/02-talent-acquisition.md` |
| 3 | Time, Attendance, Leave & Timesheets | `modules/03-time-attendance-leave.md` |
| 4 | Payroll, Statutory, Tax, Assets, Finance & Exit/F&F | `modules/04-payroll-finance.md` |
| 5 | Performance, Growth, Pulse AI & Reporting | `modules/05-performance-growth-pulse-reports.md` |
| 6 | Super-Admin / SaaS control plane | `modules/06-super-admin-saas-control-plane.md` |
| 10 | **Master feature inventory** (Step 2) | `10-feature-inventory.md` |
| 11 | **Business Requirements Document** (Step 4) | `11-business-requirements-brd.md` |
| 12 | **Gap analysis** (Step 3) | `12-gap-analysis.md` |
| 13 | **Workflow documentation** | `13-workflow-documentation.md` |
| 14 | **Dependency map** (Step 6) | `14-dependency-map.md` |
| 15 | **Implementation roadmap** (Step 7) | `15-implementation-roadmap.md` |
| 16 | **Architecture blueprint** (Step 8) | `16-architecture-blueprint.md` |
| 17 | **Technology stack** (Step 9) | `17-technology-stack.md` |
| 18 | **Database design** | `18-database-design.md` |
| 19 | **API blueprint** | `19-api-blueprint.md` |
| 20 | **Security architecture** | `20-security-architecture.md` |
| 21 | **Integration strategy** | `21-integration-strategy.md` |
| 22 | **Reporting & analytics strategy** | `22-reporting-strategy.md` |
| 23 | **Future expansion strategy** | `23-future-expansion.md` |

## How to read this blueprint

- **Product/BA**: start at `00`, then `10` (features), `11` (BRD), `13` (workflows).
- **Architects/Tech leads**: `14` (dependencies) → `15` (roadmap) → `16` (architecture) → `17` (stack) → `18` (DB) → `19` (API).
- **Security/Compliance**: `20`, plus `12` gap items tagged `[COMPLIANCE]`.
- **Per-team engineers**: your module spec under `modules/`, cross-referenced with `18` (DB) and `19` (API).

## Provenance & confidence legend

Every requirement is tagged:
- **`[D]` Available in Design** — directly observed in the HTML/JS (screen, field, action, status, or workflow present).
- **`[I]` Implied by Design** — strongly inferable from design intent (e.g. a status badge implies a state machine; an "Approve" button implies a notification).
- **`[M]` Missing but Required** — not in the design but mandatory for an enterprise iHRMS; justified by HR/payroll/SaaS industry standards and Indian statutory law.

The prototype is a **front-end-only simulation**: all data is in-memory JS literals, all actions are toasts, there is no persistence, no auth, no real validation, and no server. Therefore *everything* in the backend, persistence, security, and integration layers is `[I]`/`[M]` — the design tells us **what** the system does, this blueprint specifies **how** to build it for real.

## Scale targets (from control-plane design)

- Multi-tenant: **12 tenants** modeled, priced **PEPM** (per-employee-per-month) — architecture must scale to **thousands of tenants** and **millions of employees**.
- Data residency: **3 regions** modeled (India / EU / US) — architecture must support region-pinned tenant data.
- Modules are independently **entitled per tenant** (15 modules in the catalog) — architecture must gate features per tenant subscription.
