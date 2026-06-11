# 10 — Master Feature Inventory (Step 2)

Every feature discovered in the design, grouped by domain. Tags: `[D]` in design, `[I]` implied, `[M]` missing-but-required. Module specs under `modules/` hold the per-screen detail; this is the consolidated catalogue used for scoping and the WBS.

---

## A. Platform & Tenancy (Control Plane)

### A1. Tenant Management `[D]`
- Tenant directory with status (trial / active / attention / suspended / archived), plan, region, employee count, MRR.
- Tenant workspace drawer: Profile, Subscription, Modules, Users, Health, Support, Audit.
- Per-tenant module entitlement toggles (15 modules).
- Data residency assignment (India / EU / US) `[D]`; region-pinned storage `[M]`.
- Tenant provisioning & deprovisioning automation `[M]`.

### A2. Plans, Entitlements & Catalog `[D]`
- Plan tiers, module catalog, entitlement matrix, plan comparison, add-ons, trials.
- PEPM pricing model; plan↔entitlement↔metering consistency engine `[M]`.

### A3. Billing & Revenue `[D]`
- Subscriptions, usage metering, invoices (GST), payments, disputes, revenue analytics.
- Usage-based/overage billing reconciliation `[M]`; dunning & payment-gateway integration `[M]`.

### A4. Release Governance `[D]`
- Feature flags (with targeting, rollout %, prerequisites, per-tenant overrides, kill switch, audit), version rings (7 rings), rollouts, rollbacks, beta programs, release notes.

### A5. Compliance & Statutory Governance `[D]`
- Compliance packs with 8-state publish workflow (draft → legal_review → sandbox_preview → impact_analysis → approved → published → acknowledged → archived).
- Versions, impact analysis, publish queue, acknowledgements, evidence bundles, legal sources, rollback history.
- India statutory rate master (EPF, ESI, income tax slabs, surcharge, gratuity, perquisite, PT) with change history.

### A6. Announcements & Templates `[D]`
- Platform announcements (draft/scheduled/published, templates, analytics).
- Global template library (HR, Payroll, Performance, Workflow, Compliance, Documents) with tenant install tracking.

### A7. Integrations Hub (platform) `[D]`
- Integration providers, connected tenants, failed syncs, webhooks, API keys, logs; provider config drawer.

### A8. Security & Trust (platform) `[D]`
- MFA policy, SSO/SAML, IP restrictions, sessions, login-as/impersonation (approval + masking), data masking, secrets vault, incidents.

### A9. AI Governance `[D]`
- AI providers, models, tenant policies, prompt templates, token budgets, usage, redaction, AI audit, kill switches.

### A10. Observability `[D]`
- System health, jobs, queues, API logs, integration logs, payroll runs, error trends, uptime.

### A11. Data Governance `[D]`
- Retention, residency, data export, legal hold, deletion, PII masking, evidence, backup policies, restore (sandbox-first, dual-approval), DR tests.

### A12. Developer Platform `[D]`
- API keys, webhooks (9 event types), event catalogue, API usage, documentation, sandbox.

### A13. Support `[D]`
- Tickets, tenant health, impersonation requests, incidents, RCA, customer notes.

### A14. Platform Settings `[D]`
- Countries, currencies, languages, time zones, industries, defaults, notifications, branding, environment, security defaults, AI defaults, compliance defaults.

---

## B. Identity, RBAC & Workflow (Foundation, tenant)

### B1. Identity & Persona `[D]`
- 7 personas with feature-gated nav; single identity candidate→employee `[D]`.
- Real auth (password, SSO, MFA), session management `[M]`.

### B2. RBAC & Role Catalog `[D]`
- `ROLE_CATALOG`, `ROLE_DESIGNATIONS`, scope levels, role editor with icon library.
- Field-level & action-level permissions, segregation of duties (approver ≠ requester) `[M]`.

### B3. Workflow & Approval Engine `[D]`
- 19 request types → 8 groups; ordered routing steps; role resolution (org-chart auto / designated pool / specific person); any/all modes; amount-gated escalation (5 comp tiers by ₹).
- SLA model: slaHrs × slaBasis (business/calendar), approaching %, on-breach actions (reminder/escalate/visual/auto-finalize), reminder intervals, channels.
- In-flight workflow snapshotting (immune to mid-flight config change) `[M]`; real SLA clock + business-calendar engine `[M]`.

### B4. Delegation `[D]`
- Type-scoped, date-windowed, non-nested delegations; accountability stays with principal.
- Scheduler-enforced activation/expiry `[M]`.

### B5. Unified Task Inbox `[D]`
- Awaiting-me / by-me / all / urgent across all modules; multi-hat aggregation.

### B6. Notifications `[I]`
- Channels declared (`NOTIFICATION_CHANNELS`); reminder intervals declared.
- Actual notification engine (email/SMS/push/in-app/WhatsApp), templating, preferences, digest `[M]`.

### B7. Audit & Activity `[I]`
- Activity surfaces in UI; TS_AUDIT_LOG exists for timesheets.
- Tamper-evident, immutable, system-wide audit log with 7-yr retention `[M]`.

### B8. Document Management `[I]`
- Documents referenced across profile, onboarding, exit, payroll.
- Generation (PDF), storage, e-sign, versioning, retention `[M]`.

---

## C. Core HR

### C1. Employee Master / Directory `[D]`
- Workforce list, filters, search, bulk operations, letter generation, org placement.
- Normalized employee entity with full HRIS fields `[M]` (prototype hardcodes literals).

### C2. Employee 360 Profile `[D]`
- 8 tabs: personal (family/dates/other), job, compensation, time (leave/attendance), compliance (disciplinary), documents, performance, more.
- Sub-tabs for personal/time/compliance.

### C3. Org Structure `[I]`
- Departments, designations, bands/grades, reporting manager, skip-level.
- Full org-chart entity (matrix, dotted-line, vacancies, effective-dated) `[M]`.

### C4. Employee Self-Service (ESS) `[D]`
- 9 tabs: Home, Attendance & Time, Leave & OOD, Payroll & Tax, Claims, My Assets, My Requests, My Profile, Performance.
- 8 self-service request forms (leave, regularization, OOD/WFH, advance, claim, profile update, declaration, asset request).
- Payslip viewer, announcements, claims, requests tracking.

### C5. Helpdesk / Requests `[D]`
- 19 request types routed through workflow engine; status tracking.
- Full HR case management (categories, SLA, knowledge base) `[M]`.

---

## D. Talent Acquisition

### D1. Workforce Planning `[D]` — headcount, positions, bands, grades, budget.
### D2. Requisitions `[D]` — create, approval chain (HM→BU Head→Finance→HR), status, SLA.
### D3. Recruiting / ATS `[D]` — pipeline (Kanban), candidates, sourcing, internal mobility; 9-stage lifecycle.
### D4. Sourcing `[D]` — job boards (LinkedIn/Naukri/Indeed/Monster/Foundit), referrals, campus, agencies, career portal.
### D5. Interviews `[D]` — calendar, list, panels, assessments, scorecards; video provider integration.
### D6. Offers `[D]` — offer creation, approval, e-sign, acceptance → BGV trigger.
### D7. BGV `[D]` — cases, packages, vendors (AuthBridge/IDfy/OnGrid/SpringVerify/First Advantage/HireRight), 9 check types, consent, adjudication.
### D8. Onboarding `[D]` — task templates (HR/IT/Admin/Manager/Employee owners), candidate portal progressive unlock, Day-1 identity issuance.
### D9. Probation `[D]` — 30-60-90 checkpoints, confirm/extend, links to performance.
### D10. TA Analytics `[D]` — funnel, source effectiveness, time-to-fill, bottlenecks.
### D11. Candidate Portal `[D]` — single-identity progressive-unlock, docs, e-sign, tasks → ESS handoff.
### D12. AI recruiting `[D/I]` — JD gen, match scoring, interview summaries, proctoring, drop-risk, fraud/OCR.

---

## E. Time, Attendance, Leave

### E1. Attendance Capture `[D]` — multi-source (biometric, GPS, face, web, mobile, manual), per-employee source allowlist, reconciliation engine.
### E2. Shifts & Rostering `[D]` — shifts, rotations, employee/dept/location default shifts.
### E3. Holidays & Locations `[D]` — holiday calendars, locations, employee-location mapping.
### E4. Regularization `[D]` — request types (missing in/out, wrong time, face/GPS failed), config, approval.
### E5. Overtime `[D]` — OT pending, approval (manual/auto), policy tiers.
### E6. Attendance Approval & Override `[D]` — L1/L2 day approval, auto-finalize, override log.
### E7. Leave Management `[D]` — leave types config, balances matrix, requests, team calendar, half-day; accrual engine `[M]`.
### E8. Comp-off `[D]` — ledger, claim, expiry.
### E9. OOD / WFH `[D]` — duty pre-approval (replaces deprecated leave-type WFH/OOD), auto attendance creation.
### E10. Geofencing & device integration `[M]` — GPS+selfie validation, biometric device sync.

---

## F. Timesheet & Project Time

### F1. Timesheet entry `[D]` — weekly grid + day entry, billable/non-billable categories, copy-week.
### F2. Projects/Clients/Tasks `[D]` — client, project (billing model: T&M/fixed/retainer/internal), tasks, industry presets.
### F3. Timesheet approval `[D]` — draft→submitted→PM-approved→approved, freeze/lock.
### F4. Billing & rate cards `[D]` — rate cards, billing rollups, invoicing inputs.
### F5. Utilization & team views `[D]` — utilization %, team timesheets, project hours.
### F6. Cost centers `[D]` — budgets, actuals, committed, amount-tier approvals.

---

## G. Payroll, Statutory & Tax

### G1. Salary structures `[D]` — components (earning/deduction/reimbursement/employer), calc types (fixed, %basic, %ctc, %gross, balancing, slab, computed, formula), tax treatment (taxable/partial/exempt), structures, pay groups.
### G2. Payroll run engine `[D]` — draft→preview→approved→bankfile→paid, holds, custom rules, register, employer cost.
### G3. Statutory `[D]` — PF/ESI/PT/TDS/gratuity rates + history; calendar-month establishment-wide consolidation.
### G4. Tax & declarations `[D]` — old/new regime, FY declarations, investment proof verification.
### G5. Advances & loans `[D]` — purposes, schedules, request→active→paid_off lifecycle.
### G6. Bank & disbursement `[D]` — company accounts, bank file generation; NEFT/H2H + UTR reconciliation `[M]`.
### G7. Payslip & statutory documents `[M]` — payslip PDF, Form 16, 24Q, PF ECR, ESIC, PT challan.
### G8. Arrears/retro & GL posting `[M]`.

---

## H. Assets & Access

### H1. Asset registry `[D]` — 15 categories, 10 statuses, lifecycle.
### H2. Asset requests `[D]` — draft→manager→IT→finance→procurement→fulfilled→acknowledged.
### H3. Licenses & access `[D]` — software licenses, access profiles/systems, provisioning/deprovisioning.
### H4. Repairs, audits, incidents `[D]` — repair lifecycle, physical audits, incident→recovery.
### H5. Depreciation `[D]` — finance view, methods, book value; period schedule engine `[M]`.

---

## I. Finance Ops

### I1. Purchase approvals `[D]` — asset purchase approval queue.
### I2. Recoveries `[D]` — cross-module recoveries (asset/loan/advance/notice/bond) feeding exit F&F.
### I3. Cost-center budgets `[D]` — budget vs actual vs committed, approval tiers.

---

## J. Performance & Growth

### J1. Goals & OKRs `[D]` — KRA/KPI/OKR/project/behaviour/learning/compliance; my/team/company; cascade (cosmetic in design).
### J2. Check-ins `[D]` — periodic check-ins.
### J3. Feedback & recognition `[D]` — received/given/recognition/360; feedback types.
### J4. Review cycles `[D]` — 10-stage cycle (draft→goal_freeze→self→manager→reviewer→calibration→final_rating→increment→outcome_release→closed).
### J5. Calibration & 9-box `[D]` — forced curve (15/25/50/8/2 advisory), 9-box grid.
### J6. Promotions & increments `[D]` — promotion readiness, increment input → payroll bridge.
### J7. PIP `[D]` — draft→active→checkpoint→improved/extended/closed/termination.
### J8. Development & careers `[D]` — dev plans, career paths, mentorship, recommendations.
### J9. Succession `[D]` — successors, key roles, readiness.
### J10. Performance analytics `[D]` — rating distribution, dept ratings, goal status.

---

## K. Exit & Full-and-Final

### K1. Exit pipeline `[D]` — draft→submitted→manager_review→retention_review→accepted→notice_period→lwd_confirmed→exited.
### K2. Knowledge transfer (KT) `[D]` — KT status workflow.
### K3. Clearance `[D]` — multi-department clearance (assets, finance, IT, HR).
### K4. F&F settlement `[D]` — earnings − recoveries − statutory = net; draft→hr_verified→finance_verified→payroll_approved→payment_processed→paid→closed.
### K5. Exit documents `[D]` — relieving/experience/service letters, no-dues, F&F statement, gratuity letter.

---

## L. Cross-cutting Intelligence

### L1. Pulse AI `[D]` — attrition risk, insights, nudges (no backing entity in prototype).
### L2. Reports `[D]` — 9 categories, 35 prebuilt definitions, period/dept/location filters, Excel/PDF/CSV/Email export, scheduled delivery, custom builder with AI suggest.
### L3. Command palette `[D]` — global search/navigation.
### L4. Dashboards `[D]` — role-specific KPI bento + AI inbox.

---

## Feature count summary

| Domain | Distinct features (`[D]`) | Major engines to build (`[M]`) |
|--------|---------------------------|-------------------------------|
| Platform/Tenancy | ~45 | provisioning, metering, residency |
| Identity/RBAC/Workflow | ~12 | auth, RBAC enforcement, SLA clock, notifications, audit |
| Core HR | ~18 | normalized HRIS, org chart |
| Talent Acquisition | ~38 | consent/retention, scheduling, dedup |
| Time/Attendance/Leave | ~28 | accrual, reconciliation→LOP, device/geo |
| Timesheet | ~16 | invoicing, locking scheduler |
| Payroll/Statutory/Tax | ~26 | TDS engine, payslip/Form16, filings, bank H2H, GL |
| Assets/Finance | ~22 | depreciation schedule, procurement |
| Performance/Growth | ~30 | normalization, comp linkage, competency framework |
| Exit/F&F | ~12 | F&F compute, document generation |
| Reports/AI | ~10 | analytics warehouse, AI services |
| **Total** | **~255 features** | **~25 foundational engines** |
