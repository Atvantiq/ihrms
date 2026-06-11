# 16 — Architecture Blueprint (Step 8)

The architecture is **derived from the requirements discovered in analysis**, not a default template. Key drivers and the decisions they force:

| Discovered requirement | Architectural consequence |
|------------------------|---------------------------|
| Multi-tenant SaaS, PEPM, thousands of tenants | Tenant isolation strategy + central control plane + metering. |
| Data residency (India/EU/US) | Region-pinned data; tenant→region routing. |
| 15 independently-entitled modules | Modular bounded contexts + entitlement gating at gateway. |
| Generic workflow engine across all modules | Workflow as a shared platform service, not per-module code. |
| Heavy async compute (payroll, reports, accruals, filings) | Job/queue workers; CQRS read models for analytics. |
| Independent dev teams, future modules | Modular monolith → selective microservices; clear contracts. |
| Immutable audit, 7-yr retention, compliance | Append-only audit store; event sourcing for sensitive flows. |
| Statutory packs published centrally | Config-as-data + publish/subscribe to tenants. |

## 16.1 Chosen style: **Modular Monolith → Strangler-to-Microservices**, two planes

**Decision:** Start as a **modular monolith** per plane (one tenant-app deployable, one control-plane deployable) with **strict module boundaries** (bounded contexts, no cross-module DB reads — only via service interfaces/events). Extract high-load or independently-scaling contexts into microservices **when metrics justify it** (payroll compute, attendance ingestion, reporting, notifications, AI).

**Why not microservices-first:** The design reveals dense cross-module coupling (single identity, payroll sinks, F&F integrator). A microservices-first split would create distributed-transaction and latency pain before product-market scale. A modular monolith with clean seams gives team autonomy *and* an extraction path. This is the lowest-risk route to the stated scale.

**Why not a single monolith forever:** Payroll runs, attendance ingestion, report generation, and AI have radically different scaling/SLA profiles and must be independently scalable — hence planned extraction.

## 16.2 High-level topology

```
                         ┌────────────────────────┐
   Web (tenant) ───────► │  CDN / WAF / API Gateway│ ◄─────── Mobile (tenant)
   Web (super-admin) ──► │  (authN, rate-limit,    │ ◄─────── Public API clients
                         │   entitlement, routing) │ ◄─────── Webhooks out
                         └───────────┬─────────────┘
            ┌──────────────────────── │ ──────────────────────────┐
            ▼                         ▼                            ▼
 ┌───────────────────┐   ┌───────────────────────────┐  ┌──────────────────┐
 │  CONTROL PLANE    │   │      TENANT PLANE          │  │ SHARED PLATFORM  │
 │  (modular monolith)│  │   (modular monolith)       │  │   SERVICES       │
 │  Tenants, Plans,  │   │  Bounded contexts:         │  │ Identity/Auth    │
 │  Billing/Metering,│   │   CoreHR · TA · Time ·     │  │ Workflow engine  │
 │  Releases/Flags,  │   │   Leave · Timesheet ·      │  │ Notification     │
 │  Compliance packs,│   │   Payroll · Assets ·       │  │ Audit            │
 │  Security, AI gov,│   │   Performance · Exit ·     │  │ Document/e-sign  │
 │  Observability,   │◄──┤   Reports · Pulse          │──┤ Search           │
 │  Data gov, Dev/API│   │                            │  │ Job/Scheduler    │
 └─────────┬─────────┘   └─────────────┬──────────────┘  └────────┬─────────┘
           │                           │                          │
           ▼                           ▼                          ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │ DATA: Postgres (per-region, tenant-isolated) · Redis · Object store ·  │
 │ Event bus (Kafka) · Search (OpenSearch) · OLAP/warehouse (analytics)   │
 └───────────────────────────────────────────────────────────────────────┘
```

## 16.3 Multi-tenancy strategy

**Decision: hybrid — shared schema with `tenant_id` row-level isolation for most data; schema-per-tenant or DB-per-tenant for large/regulated tenants; region-pinned clusters.**

- **Default (SMB/mid):** shared Postgres, every table carries `tenant_id`, enforced by **Postgres Row-Level Security (RLS)** policies bound to a session `tenant_id` claim. Cheap, dense, easy to operate.
- **Enterprise/large tenants:** option to provision a **dedicated schema or database** (the control plane already models per-tenant deployment stamps & residency) for noisy-neighbour isolation and stricter data boundaries.
- **Residency:** each region (India/EU/US) is a separate cluster; a tenant is pinned to one region at provisioning; the gateway routes by tenant→region map. No cross-region tenant data movement.
- **Isolation guarantees:** every query path carries `tenant_id`; RLS is the backstop; platform-operator cross-tenant access only via the **audited impersonation** service with masking.

**Why RLS-first:** It pushes tenant isolation into the database as a hard guarantee (defence in depth) rather than relying solely on application discipline, while keeping infra costs viable at thousands of tenants.

## 16.4 Bounded contexts & ownership

Each context owns its tables, exposes a service API, and publishes domain events. No context reads another's tables directly.

| Context | Owns | Publishes events | Consumes |
|---------|------|------------------|----------|
| Identity/Tenancy | users, sessions, tenants, entitlements | `user.*`, `tenant.*` | — |
| Core HR | employees, org, profile, documents-refs | `employee.hired/updated/terminated`, `org.changed` | TA (hire), Exit (terminate) |
| Talent Acquisition | reqs, candidates, offers, BGV, onboarding | `candidate.*`, `offer.accepted`, `employee.day1` | headcount, Core HR |
| Time & Attendance | events, shifts, regularizations, OT | `attendance.finalized`, `ot.approved` | device adapters |
| Leave & OOD | leave types, balances, requests, comp-off | `leave.approved`, `accrual.posted` | Attendance |
| Timesheet | projects, timesheets, cost centers | `timesheet.approved` | Core HR |
| Payroll | structures, runs, statutory, tax, advances | `payroll.finalized`, `payslip.published`, `increment.applied` | Attendance, Leave, Performance, Assets |
| Assets & Access | assets, requests, licenses, access | `asset.allocated`, `access.provisioned`, `recovery.raised` | IT systems |
| Performance | goals, reviews, calibration, PIP, increments | `increment.approved`, `pip.termination` | Core HR |
| Exit & F&F | exit cases, clearance, F&F | `exit.initiated`, `fnf.paid` | Payroll, Assets, Leave |
| Reports/Pulse | read models, schedules | — | all events |
| Workflow (shared) | workflow defs, instances, tasks | `task.created`, `request.approved/rejected`, `sla.breached` | all |
| Notification (shared) | templates, deliveries, prefs | `notification.sent` | all |
| Audit (shared) | append-only events | — | all |
| Document (shared) | templates, generated docs, signatures | `document.generated`, `document.signed` | all |

## 16.5 Eventing & consistency

- **Synchronous** for user-facing reads/writes within a context (strong consistency).
- **Asynchronous events** (Kafka) for cross-context side-effects (offer.accepted → BGV; payroll.finalized → GL; exit → clearance). Eventual consistency with idempotent consumers and outbox pattern.
- **Saga orchestration** for multi-context long-running processes (hire-to-onboard, exit-to-F&F): a process manager per macro-workflow coordinates steps and compensations.
- **Event sourcing** for the highest-integrity flows (payroll runs, audit, approvals) to give a replayable, tamper-evident history; CRUD elsewhere.

## 16.6 Read models & analytics (CQRS)

- Operational stores stay normalized for transactional integrity.
- A **CDC pipeline** (Debezium → Kafka) streams changes into an **OLAP warehouse** (per-region) powering Reports, Pulse AI, dashboards, and metering — keeping heavy analytics off the transactional path.

## 16.7 Async compute

Dedicated worker pools (scaled independently) for: payroll runs, leave accruals, attendance reconciliation, statutory filing generation, report scheduling, notification fan-out, integration syncs, AI inference. Backed by a durable queue; jobs are observable (the control-plane already models jobs/queues/uptime).

## 16.8 API & extensibility

- **API Gateway** terminates auth, enforces tenant entitlement + rate limits, routes by region.
- **Public REST/GraphQL API** + **webhooks** (control plane already defines 9 webhook event types) for third-party and mobile.
- **Versioned contracts**; backward-compatible evolution; sandbox environment (modeled in super-dev).

## 16.9 Availability & scale

- Stateless app tiers behind load balancers; horizontal autoscaling.
- Postgres primary + read replicas per region; partition large tables by `tenant_id`/time (attendance_events, audit).
- Redis for sessions, caching, rate-limit, locks.
- Multi-AZ; documented RPO/RTO; periodic DR tests (control plane models DR).
- Payroll for 10k employees in <10 min via partitioned parallel workers.

## 16.10 Deployment & environments

- Containers (Kubernetes) per region; blue/green or canary aligned with the control plane's **version rings & feature flags** (the product *is* its own progressive-delivery system).
- Environments: sandbox, staging, production per region; IaC; per-tenant feature flags drive rollout.

## 16.11 Key architectural decisions (ADR summary)

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-1 | Modular monolith per plane, extract later | Dense coupling; team autonomy without distributed-txn pain. |
| ADR-2 | Postgres + RLS, hybrid isolation, region-pinned | Hard tenant isolation + residency + cost viability at scale. |
| ADR-3 | Shared platform services (workflow/notify/audit/doc/identity) | Design treats these as cross-cutting; build once. |
| ADR-4 | Event-driven cross-context + sagas | Decouples sinks (payroll/F&F) from feeders; long-running flows. |
| ADR-5 | Event sourcing for payroll/audit/approvals | Tamper-evident, replayable, compliance-grade history. |
| ADR-6 | CQRS warehouse via CDC | Keeps analytics & metering off transactional path. |
| ADR-7 | Entitlement gating at gateway | 15 per-tenant modules; enforce centrally. |
| ADR-8 | Config-as-data statutory packs | Statutory currency without code deploys. |
