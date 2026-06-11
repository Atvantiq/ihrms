# 12 — Gap Analysis (Step 3)

The prototype is **UI-complete but engine-empty**. This document classifies every significant gap as:
- **Available in Design `[D]`** — present and usable in the prototype (listed for completeness/context).
- **Implied by Design `[I]`** — the UI presumes it exists (a status badge implies a state machine; an Approve button implies notification + audit).
- **Missing but Required `[M]`** — absent from design but mandatory for a real enterprise iHRMS, with justification.

Every `[M]` includes **why it's required**.

---

## 12.1 Foundation / platform-wide gaps (highest priority — block everything)

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-F1 | **Persistence layer** (DB) | M | Prototype mutates in-memory arrays; nothing survives reload. Everything depends on this. |
| G-F2 | **Authentication & session** (password, SSO/SAML, MFA) | M | No login exists; control plane *governs* SSO/MFA but tenant app has none. Enterprise procurement blocker. |
| G-F3 | **RBAC enforcement** (server-side, field & action level) | M | Personas only hide UI; no server authorization. Data-leak & SoD risk. |
| G-F4 | **Notification/reminder engine** (email/SMS/push/in-app/WhatsApp) | M | Channels & intervals are declared (`NOTIFICATION_CHANNELS`) but inert. Approvals/SLAs are meaningless without it. |
| G-F5 | **SLA clock + business-calendar engine** | M | `slaBreached` is hardcoded; no real timer, holiday calendar, or working-hours math. |
| G-F6 | **Immutable audit log** (system-wide) | M | Audit arrays are mutable, diffs are placeholders. SOC2/DPDP/SOX require tamper-evident audit, 7-yr retention. |
| G-F7 | **Document generation & storage** (PDF, templates, versioning) | M | Payslips, offer/relieving/experience letters, Form 16, F&F statements are referenced but never produced. |
| G-F8 | **E-signature** integration | I/M | Offers & onboarding reference e-sign; no provider wired. |
| G-F9 | **Validation framework** (PAN/Aadhaar/IFSC/email/GST, caps, rules) | M | No input validation anywhere; data integrity & statutory correctness depend on it. |
| G-F10 | **Workflow snapshotting** | M | Routing/role changes mid-flight would corrupt in-flight approvals; need versioned snapshot at submit. |
| G-F11 | **File/object storage + AV scanning** | M | Document uploads everywhere; no storage, no malware scanning. |
| G-F12 | **Search/indexing** | I | Command palette & directory search imply an index (employees, candidates, docs). |
| G-F13 | **Background job/queue system** | M | Payroll runs, report scheduling, accruals, reminders, syncs all need async workers (control plane shows jobs/queues but tenant app has none). |
| G-F14 | **Multi-tenant data isolation + residency pinning** | M | Region modeled in control plane; tenant data must be physically region-pinned & isolated. |

---

## 12.2 Core HR gaps

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-HR1 | Normalized **Employee entity** with full HRIS fields | M | `EMPLOYEES_MASTER` has ~6 fields; real HRIS needs 80+ (statutory IDs, bank, nominee, education, employment history, effective-dated job/comp). |
| G-HR2 | **Effective-dated org & job history** | M | No history; compliance & analytics need point-in-time org/comp. |
| G-HR3 | **Org-chart engine** (matrix, dotted-line, vacancies, cycles) | M | Single `managerId` hop is fragile; routing resolution breaks on vacancy/matrix. |
| G-HR4 | **Consent & data-retention lifecycle** (DPDP Act) | M | PII collected (candidate→employee→alumnus) without consent capture or retention/erasure. Legal requirement. |
| G-HR5 | **HR case management** (helpdesk SLA, KB) | I | 19 request types imply ticketed case management beyond simple routing. |

---

## 12.3 Talent Acquisition gaps

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-TA1 | Requisition **rejection/return path** with reasons | M | Only forward approval modeled; real approvals reject/rework. |
| G-TA2 | **Offer negotiation/versioning** & re-approval | M | Offer edits are cosmetic; counter-offers need versioned re-approval. |
| G-TA3 | **BGV consent & data lifecycle** (DPA, retention, deletion) | M | BGV shares PII with vendors; DPDP/GDPR mandate consent, DPA, retention. |
| G-TA4 | **Interviewer availability & panel scheduling** | M | Analytics flags panel availability as the bottleneck; no scheduling engine exists. |
| G-TA5 | **Duplicate-candidate detection** | M | Re-applicants/fraud; dedup on email/phone/PAN. |
| G-TA6 | **Writeback to headcount/budget** on req/offer | M | Reqs/offers don't decrement `TA_HEADCOUNT`; planning becomes inaccurate. |
| G-TA7 | **Confirmation hard-gate** (review + learning + BGV) | M | Probation confirmation should be gated, not free-clicked. |

---

## 12.4 Time / Attendance / Leave gaps

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-T1 | **Leave accrual engine** (anniversary/calendar, pro-rata, carry-forward, expiry, encashment) | M | Balances are static; accrual is core to leave. |
| G-T2 | **Attendance→payroll LOP/OT pipeline** | M | Reconciliation exists in UI but doesn't compute LOP/OT into payroll. |
| G-T3 | **Biometric/face device integration** | M | Sources declared but no device sync (ONAQT/ESSL/eSSL/cloud). |
| G-T4 | **Geofencing + selfie validation** | M | Mobile/GPS source needs server-side geo & liveness validation. |
| G-T5 | **Penalty/sandwich/blackout rule engine** | M | Tiers declared (`TA_PENALTIES`) but not computed; sandwich & blackout unenforced. |
| G-T6 | **Negative-balance & balance validation** | M | Leave can be applied beyond balance; needs enforcement. |
| G-T7 | **Auto-finalize & reminder scheduler** | M | Day-approval auto-finalize is decorative without a scheduler. |

---

## 12.5 Timesheet gaps

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-TS1 | **Invoice generation** from approved billable time | M | Rate cards & billing rollups exist but no invoice output. |
| G-TS2 | **Period lock scheduler** | M | Freeze/lock is manual; needs scheduled period close. |
| G-TS3 | **Capacity/leave-aware utilization** | I | Utilization should net out approved leave/holidays. |

---

## 12.6 Payroll / Statutory / Tax gaps (statutory-critical)

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-P1 | **TDS computation engine** (slabs, rebate 87A, surcharge, cess, both regimes, projection) | M | Tax is declared but not computed; payroll is incorrect without it. |
| G-P2 | **Payslip PDF generation** | M | Payslips referenced, never produced; legal pay-record requirement. |
| G-P3 | **Form 16 / 24Q / 12BA** e-TDS returns | M | Statutory annual/quarterly filings; legally mandatory. |
| G-P4 | **PF ECR / ESIC / PT challan** generation | M | Monthly statutory filings; legally mandatory. |
| G-P5 | **Bank file format + NEFT/H2H + UTR reconciliation** | M | Disbursement modeled but no real bank file/integration/reconciliation. |
| G-P6 | **GL/journal posting** to accounting | M | Export-only today; finance needs journal entries to ERP. |
| G-P7 | **Arrears / retro recompute** | M | Mid-cycle changes & back-dated increments need retro. |
| G-P8 | **Full state-wise PT & LWF master** | M | Only partial; PT/LWF vary by state. |
| G-P9 | **Maker-checker & reconciliation controls** | M | Payroll requires dual control & variance checks before disbursement. |

---

## 12.7 Assets / Finance gaps

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-A1 | **Period depreciation schedule engine** | M | Book values are hardcoded; needs SLM/WDV schedules. |
| G-A2 | **Procurement/PO integration** | I | Asset request reaches "procurement" stage but no PO system. |
| G-A3 | **Access deprovisioning automation (SCIM)** | M | Access provisioning is manual; exit needs automated revoke. |

---

## 12.8 Performance gaps

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-PF1 | **Goal cascade/alignment roll-up** | M | `linked` is free-text; OKR alignment needs real roll-up. |
| G-PF2 | **Enforced normalization/bell-curve** | M | Curve is advisory; calibration needs enforcement options. |
| G-PF3 | **Comp-band / pay-equity linkage** | M | Increments not bounded by band/budget; pay-equity risk. |
| G-PF4 | **Competency/skills framework** | M | Reviews reference behaviours but no competency model. |
| G-PF5 | **Analytics warehouse / historical trending** | M | No multi-cycle history; trend analytics impossible. |
| G-PF6 | **PIP→exit linkage** | M | Termination-recommended PIP should feed exit/offboarding. |

---

## 12.9 Exit / F&F gaps

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-E1 | **F&F computation engine** (gratuity eligibility, leave encashment, notice recovery, tax) | M | F&F math modeled in UI but not executable. |
| G-E2 | **Exit document generation** (relieving/experience/no-dues/service) | M | Referenced, not produced. |
| G-E3 | **Clearance automation** (auto-revoke access/assets) | M | Clearance is checkbox; should drive real deprovisioning. |

---

## 12.10 Control-plane gaps

| ID | Gap | Class | Why required |
|----|-----|-------|--------------|
| G-S1 | **Tenant provisioning automation** | M | New tenant needs automated DB/schema/region setup. |
| G-S2 | **Usage metering & overage reconciliation** | M | PEPM revenue depends on accurate active-employee metering. |
| G-S3 | **SLA monitoring & enforcement** | M | Support SLAs displayed, not enforced/alerted. |
| G-S4 | **True audit immutability** | M | In-memory mutable; needs append-only store (WORM/hash-chain). |
| G-S5 | **SCIM / directory sync + deprovisioning** | M | Enterprise SSO needs SCIM provisioning. |
| G-S6 | **Public status page & incident comms** | M | Enterprise SLA expectation. |
| G-S7 | **Plan↔entitlement↔metering source-of-truth** | M | Three views can drift; need one consistent model. |
| G-S8 | **Real AI budget/kill-switch enforcement + redaction** | M | Governed in UI; must actually gate provider calls & redact PII. |
| G-S9 | **DR/backup verification with RPO/RTO** | M | DR tests modeled; need real backup/restore verification. |
| G-S10 | **Enforced dual-approval workflows** (restore, secrets, impersonation) | M | Shown but not enforced. |

---

## 12.11 Missing entities (consolidated)

Entities the design implies but does not model: `User/Credential`, `Session`, `AuditEvent`, `Notification`, `NotificationTemplate`, `Document`, `DocumentTemplate`, `Signature`, `ConsentRecord`, `OrgUnit`/`Position` (effective-dated), `JobHistory`, `CompensationHistory`, `LeaveAccrualTransaction`, `AttendanceDeviceEvent`, `Geofence`, `TDSComputation`, `StatutoryFiling`, `BankTransaction`, `GLJournal`, `DepreciationSchedule`, `Invoice` (timesheet billing), `PurchaseOrder`, `CompetencyFramework`, `PerformanceHistory`, `MeteringRecord`, `WebhookDelivery`, `BackgroundJob`.

## 12.12 Missing integrations (consolidated)

Identity (SSO/SAML/OIDC, SCIM), banks (NEFT/RTGS/IMPS H2H), statutory portals (EPFO, ESIC, Income Tax TRACES, state PT), payment gateway (billing), e-sign (DocuSign/Leegality/Digio), BGV vendors (API), job boards, video (Zoom/Meet/Teams/Webex), calendar (Google/Outlook), biometric devices, accounting/ERP (Tally/Zoho/SAP), communication (email/SMS/WhatsApp providers), AI/LLM providers, observability/APM.

## 12.13 Missing operational requirements

Backup/restore runbooks, DR drills, data-migration/import tooling (the design *does* include import wizards — `AE_STEPS`, `BI_STEPS` — but no validation/rollback), tenant onboarding playbook, rate-master update SOP, incident management, on-call, SLO/error budgets, observability/tracing in the tenant app (only control plane has it).
