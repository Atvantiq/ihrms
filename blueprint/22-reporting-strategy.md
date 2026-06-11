# 22 — Reporting & Analytics Strategy

The design ships a Reports module (9 categories, 35 prebuilt definitions, filters, export, scheduling, custom builder + AI suggest) plus Pulse AI (attrition) and role dashboards. This strategy makes it scalable and trustworthy.

## 22.1 Architecture: separate the read path (CQRS)

- Transactional modules stay normalized for integrity.
- **CDC (Debezium) → Kafka → warehouse (ClickHouse / Snowflake)** builds analytical read models without loading OLTP.
- Reports & dashboards query the warehouse; operational "live" lists query OLTP read models (materialized views).
- Region-pinned warehouses (residency).

```
OLTP (per context) ──CDC──► Kafka ──► Warehouse (facts/dims) ──► Reports · Dashboards · Pulse AI · Metering
```

## 22.2 Report taxonomy (9 categories from `REPORT_CATEGORIES`)

Module-aligned categories with ~35 prebuilt definitions (`REPORT_DEFS`), e.g.:

| Category | Representative reports |
|----------|------------------------|
| Payroll | Salary register, payslip summary, statutory (PF/ESI/PT/TDS), bank disbursement, CTC/cost. |
| Attendance | Monthly attendance, late/absent, OT, regularization, muster. |
| Leave | Balance, availed, encashment liability, comp-off ledger. |
| Talent Acquisition | Source effectiveness, time-to-fill, funnel, offer accept ratio, pipeline aging. |
| Performance | Rating distribution, calibration, 9-box, increment/promotion, PIP. |
| Headcount / HR | Headcount, attrition, diversity, tenure, org movements. |
| Timesheet | Utilization, billable vs non-billable, project hours, cost-center. |
| Assets | Allocation, depreciation, audit, license utilization. |
| Exit | Attrition reasons, F&F liability, exit interview themes. |

## 22.3 Capabilities (from design + completed)

- **Filters**: period, department, location (design) + role/scope-aware data restriction (added).
- **Export**: Excel, PDF, CSV, Email (design).
- **Scheduling**: cron-based delivery to recipients, active/paused (design) — runs on the job/scheduler service.
- **Custom builder**: pick source + columns + filters; **AI smart-suggest** (design) — governed by AI gateway.
- **Drill-down** from dashboard tiles to detail.
- **Scope security**: a manager's report sees only their team; HR/Finance per their scope; field masking applies in reports too.

## 22.4 Statutory & compliance reports (gap-closing, mandatory)

Beyond the prototype's set, build the legally-required registers/returns:
- **PF ECR**, **ESIC** monthly, **state PT challans**, **24Q** quarterly e-TDS, **Form 16 / 12BA** annual, **Form 24Q/26Q**, **wage register**, **muster roll**, **gratuity/bonus registers**, **LWF**.
- Generated as governed artifacts with evidence bundles (ties to compliance packs).

## 22.5 Analytics & AI (Pulse)

- **Pulse AI** (attrition risk in prototype) becomes a model over warehouse features: tenure, performance, comp percentile, attendance anomalies, engagement signals → risk scores + drivers + recommended actions.
- Additional predictive surfaces: hiring forecast vs headcount plan, payroll cost projection, leave liability forecast, utilization optimisation.
- All AI features go through the governed gateway (budgets, redaction, audit).

## 22.6 Dashboards

- **Role-specific KPI bento** (design) + AI inbox: each persona's landing dashboard (employee/manager/HR/finance/IT/reviewer).
- **Control-plane dashboards**: tenant health, MRR/revenue, usage metering, uptime, job/queue health, error trends (modeled).
- Built on warehouse read models; near-real-time via streaming aggregates where needed.

## 22.7 Metering & billing analytics (revenue-critical)

- PEPM billing depends on accurate **active-employee metering** — built on the same CDC stream (count active employees per tenant per period), reconciled against entitlements and invoices (closes G-S2/G-S7).
- Usage meters: API calls, AI tokens, storage (control plane models `SA_METERS`).

## 22.8 Governance

- **Single semantic layer / metric definitions** so "headcount", "attrition", "utilization" mean one thing everywhere (avoids the prototype's per-screen ad-hoc calcs).
- Report access audited; scheduled-report recipients validated; exports watermarked + logged (mass-export anomaly detection feeds SIEM).
- Historical retention enables multi-period trending (closes G-PF5).
