# 17 — Technology Stack (Step 9)

**Chosen stack: Next.js (React + TypeScript) frontend · Python (FastAPI) backend.** Selected for team fluency and delivery speed, validated against the analysis-derived drivers: multi-tenant scale, statutory-grade correctness, maintainability, cost efficiency, enterprise readiness, long-term growth. This document records the decisions, the rationale, and — critically — the **engineering standards that make this stack safe for payroll-grade software**.

## 17.1 Decision principles

1. **Team fluency beats theoretical ecosystem fit** — a TypeScript/Python team ships faster and maintains better in TypeScript/Python.
2. **Correctness is a discipline, not a library** — payroll accuracy comes from exact decimal arithmetic, strict typing, and rule engines; these are enforced as standards (§17.4) regardless of language.
3. **One typed contract end-to-end** — OpenAPI generated from FastAPI drives generated TypeScript clients; frontend can never drift from the API.
4. **Managed services for undifferentiated plumbing**; open standards (OIDC/SAML, OpenAPI, SQL) to avoid lock-in.

## 17.2 Frontend

| Concern | Decision | Why |
|---------|----------|-----|
| Framework | **Next.js 14+ (App Router) + TypeScript** | The prototype's 41-screen `SCREENS{}` dispatch maps directly to routes; SSR for the public surfaces (career portal, candidate/offer pages) where SEO and link-sharing matter; internal app screens stay client-rendered. |
| Styling | **Tailwind CSS + design tokens extracted from the prototype** | The prototype's design system (Prism) is built on CSS variables (`--ink`, `--mute`, `--line`, `--bg`, `--amber`, `--rose`, …) — these become the Tailwind theme; pills/badges/bento tiles become a small shared component library. |
| Server state | **TanStack Query** + generated API client | Cache-friendly, matches the data-heavy screens. |
| Client state | **Zustand** (light) | Persona/UI state only; server is the source of truth. |
| Tables | **TanStack Table + virtualization** | Payroll register, directory, timesheet grid are dense interactive tables — keep them client-rendered and virtualized. |
| Charts | **ECharts / Recharts** | Funnels, 9-box, distributions, dashboards. |
| Forms | **react-hook-form + zod** | zod schemas mirror backend Pydantic models; shared validation semantics. |
| Auth integration | next-auth / custom OIDC against the IdP | SSO-first (§20). |
| Mobile | **React Native** (ESS-first: attendance/selfie, approvals, payslips, leave) | Reuses the TS skill set and the generated API client. |

**Boundary rule:** Next.js renders; FastAPI decides. No business logic in Next.js API routes or server actions — they may proxy/compose, never compute payroll, balances, or permissions.

## 17.3 Backend

| Concern | Decision | Why |
|---------|----------|-----|
| Framework | **Python 3.12 + FastAPI** | Async-first fits the integration-heavy surface (BGV, banks, job boards, webhooks); Pydantic v2 gives the validation framework (gap G-F9) nearly for free; best ecosystem for the AI layer (Pulse, copilots, redaction gateway). |
| API contract | **OpenAPI generated from FastAPI** → generated TS clients | Single source of truth; spec-first discipline with code-first ergonomics. |
| ORM / DB access | **SQLAlchemy 2.0 (typed) + Alembic migrations** | Mature, typed, async-capable; pairs with Postgres RLS (§17.5). |
| Validation | **Pydantic v2** models at every boundary; reusable validated types for PAN/Aadhaar/IFSC/GST | Closes G-F9 as a first-class capability. |
| Long-running workflows | **Temporal (Python SDK)** for sagas: hire-to-onboard, exit-to-F&F, payroll run orchestration | Durable execution, retries, timers→SLA, compensation — exactly what the macro-workflows need. |
| Background jobs | **Celery** (or ARQ) on Redis for simple fan-out: notifications, report generation, accrual ticks, syncs | Don't put trivial jobs on Temporal; don't put sagas on Celery. |
| AuthZ | One enforcement layer (FastAPI dependency) calling **OPA/Cedar** policies | No scattered `if role:` checks; policy is testable and external. |
| Services layout | **Modular monolith** (one FastAPI app per plane, strict bounded-context packages, no cross-context imports of models) → extract later per §16 | Same architecture as specced; language-agnostic. |

### Performance posture (Python-specific)
- Most load is IO-bound (DB, integrations) — async FastAPI handles it well.
- Payroll is **parallelizable batch**: partition runs across worker processes (Temporal activities / Celery workers); 10k employees < 10 min via fan-out, not single-process speed.
- **First extraction candidate is attendance ingestion** (highest sustained throughput). If it gets hot, extract it as a lean service early — the seam is already defined in §16.4.

## 17.4 Engineering standards (non-negotiable for payroll-grade Python)

These compensate for what a Java/Spring stack enforced by default:

1. **`decimal.Decimal` for all money and rates. `float` is banned in financial modules** — enforced by a lint rule (ruff custom rule / forbidden-import check) and code review. One float in a TDS slab is a statutory bug.
2. **Strict typing everywhere**: `mypy --strict` (or pyright strict) in CI; no untyped `def`; Pydantic models at all boundaries. A 200-entity domain in loose Python is unmaintainable; in strict Python it's pleasant.
3. **Rounding policy as code**: a single shared `money.py` defining quantization (`ROUND_HALF_UP` per statutory rule), currency types, and arithmetic helpers. No ad-hoc `round()`.
4. **Golden-file payroll tests**: every statutory computation (TDS both regimes, PF caps, ESI thresholds, PT slabs, gratuity, F&F) has table-driven golden tests versioned with the statutory pack effective dates.
5. **Transaction discipline**: explicit unit-of-work per request/activity; no autocommit; idempotency keys on all unsafe operations (§19.6).
6. **Bounded contexts as packages** with import-linter contracts (`core_hr` cannot import `payroll.models`, only `payroll.api`).

## 17.5 Data stores (unchanged from analysis)

| Store | Decision | Why |
|-------|----------|-----|
| OLTP | **PostgreSQL 16**, per-region, **RLS** for tenant isolation | Hard isolation backstop independent of app language; partitioning for high-volume tables. |
| Cache/sessions/locks | **Redis** | Also Celery broker. |
| Events | **Kafka** (managed) — or start with Postgres outbox + LISTEN/NOTIFY and upgrade when volume justifies | Durable cross-context events, CDC backbone. |
| Search | **OpenSearch** | Directory, candidates, docs, command palette. |
| Objects | **S3-compatible**, region-pinned | Documents, payslips, uploads. |
| Warehouse | **ClickHouse** (or BigQuery/Snowflake managed) | Reports, Pulse, metering via CDC. |
| Audit | Append-only Postgres + hash-chain → WORM archive | Tamper-evident, 7-yr retention. |

## 17.6 Identity & security (unchanged)

**Keycloak** (or Auth0/Okta managed) for OIDC/SAML/MFA/SCIM · **Vault** for secrets · **OPA/Cedar** for policy · KMS envelope encryption for PII (PAN/Aadhaar/bank/salary). See `20-security-architecture.md`.

## 17.7 Integrations & documents

| Concern | Decision |
|---------|----------|
| PDF generation | **WeasyPrint / Typst** (Python-native HTML→PDF) or Gotenberg service — payslips, Form 16, letters, F&F statements |
| E-sign | Leegality / Digio / DocuSign (Aadhaar e-sign) |
| Email/SMS/WhatsApp | SES/Postmark + MSG91/Gupshup |
| Banking | NEFT/RTGS H2H per bank + RazorpayX/Cashfree payouts |
| Statutory | Adapters: EPFO (ECR), ESIC, TRACES (24Q/Form 16), state PT |
| BGV | AuthBridge, IDfy, OnGrid, SpringVerify, First Advantage, HireRight |
| Accounting | Tally, Zoho Books, SAP connectors (GL posting) |
| Video/Calendar | Zoom/Meet/Teams/Webex; Google/Outlook (Graph) |
| Billing payments | Stripe (global) / Razorpay (India) |
| AI/LLM | Provider-abstracted governed gateway (Claude/OpenAI/Azure) — Python-native, budgets/redaction/kill-switches per control-plane model |

## 17.8 Monorepo & DevX

```
repo/
  apps/
    web/          Next.js tenant app + control-plane app
    mobile/       React Native (later)
  services/
    api/          FastAPI modular monolith (bounded-context packages)
    workers/      Temporal workers + Celery workers
  packages/
    api-client/   generated TS client from OpenAPI  ← contract bridge
    ui/           Tailwind tokens + shared components (from prototype design system)
    config/       shared lint/tsconfig
  infra/          Terraform, K8s manifests
```
- **Turborepo/Nx** for the TS side; **uv/poetry** for Python; one CI pipeline.
- Contract check in CI: regenerate client from OpenAPI → fail on uncommitted diff.

## 17.9 Platform / DevOps (unchanged)

Kubernetes (per region) · Terraform · GitHub Actions · OpenTelemetry → Prometheus/Grafana/Loki + Sentry · progressive delivery via the product's own feature flags/version rings.

## 17.10 Stack summary

```
Frontend:  Next.js (App Router) + TypeScript · Tailwind (Prism tokens) · TanStack Query/Table · zod · ECharts · React Native
Backend:   Python 3.12 + FastAPI · Pydantic v2 · SQLAlchemy 2 + Alembic · Temporal (sagas) · Celery (jobs) · OPA
Standards: Decimal-only money · mypy --strict · golden-file statutory tests · import-linter contexts · idempotency
Data:      PostgreSQL 16 (RLS, region-pinned) · Redis · Kafka (or outbox→upgrade) · OpenSearch · S3 · ClickHouse
Identity:  Keycloak/Auth0 (OIDC/SAML/MFA/SCIM) · Vault · KMS envelope encryption
Docs/Int:  WeasyPrint/Gotenberg PDF · Leegality e-sign · SES+MSG91 · bank H2H/RazorpayX · statutory adapters
Platform:  Kubernetes · Terraform · GitHub Actions · OpenTelemetry/Grafana/Sentry · feature flags/rings
AI:        Python-native governed gateway (Claude/OpenAI/Azure) with budgets, redaction, kill-switches
```

## 17.11 Risks of this stack & mitigations

| Risk | Mitigation |
|------|------------|
| Loose typing erodes a 200-entity domain | `mypy --strict` + Pydantic everywhere (CI-gated). |
| Float contamination in money paths | Decimal-only standard + lint ban + golden tests. |
| Python per-core throughput (attendance ingestion) | Async + horizontal workers; pre-defined extraction seam if hot. |
| Batch orchestration less batteries-included than Spring Batch | Temporal for sagas/payroll orchestration; Celery for fan-out. |
| Business logic leaking into Next.js | "Next renders, FastAPI decides" rule; no compute in server actions. |
| Contract drift FE↔BE | Generated TS client from OpenAPI, CI diff check. |

## 17.12 Build-vs-buy (unchanged)

**Build:** HR/payroll domain, workflow/approval engine, control plane (core IP). **Buy/managed:** identity, e-sign, BGV, banking payouts, PDF infra, comms, search/queue/warehouse, statutory connectors where vendor SDKs exist.
