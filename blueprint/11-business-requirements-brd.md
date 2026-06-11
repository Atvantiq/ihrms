# 11 — Business Requirements Document (Step 4)

## 11.1 Vision & business objectives

**Vision.** A multi-tenant SaaS iHRMS that manages the entire employee lifecycle (Hire → Onboard → Manage → Pay → Grow → Exit) for Indian enterprises, sold per-employee-per-month, with a platform-operator control plane governing tenants, billing, compliance, and security.

**Primary business objectives (derived from design intent):**
1. Single system of record for the full employee lifecycle — one identity from candidate to alumnus.
2. Statutory-compliant Indian payroll & filings, kept current centrally (compliance packs + rate master).
3. Configurable approvals so each tenant models its own org without code changes (workflow engine).
4. Per-tenant modular monetisation (15 entitled modules, PEPM).
5. Trust & governance fit for enterprise procurement (SSO, audit, data residency, DR, AI governance).

## 11.2 Stakeholders & actors

### Tenant-side personas (`PERSONAS`)
| Persona | Code | Scope | Key responsibilities |
|---------|------|-------|----------------------|
| Employee | `employee` | Self only | ESS: apply leave/OOD/claims/advances, view payslips, declarations, goals. |
| Manager | `manager` | Team | Approve team requests, attendance L1, timesheets, goals/reviews. |
| IT/Admin | `it` | Operations | Asset/access provisioning, attendance ops, system config. |
| Finance | `finance` | Finance lens | Payroll, statutory, asset depreciation, recoveries, cost centers. |
| HR | `hr` | People lifecycle | Hiring, onboarding, payroll input, performance, exit, policy. |
| Reviewer/HOD | `reviewer` | Review & approve | Calibration, L2 approvals, talent decisions. |
| Super (tenant admin) | `super` | Everything in tenant | Tenant configuration, all modules. |

### Platform-side roles (`SA_ROLES`)
| Role | Scope |
|------|-------|
| Platform Owner (`owner`) | Full platform. |
| Platform Operations (`ops`) | Tenants, support, observability. |
| Release Manager (`release`) | Releases, flags, catalog. |
| Compliance Admin (`compliance`) | Compliance packs, announcements, audit. |
| Billing Admin (`billing`) | Billing, plans, invoices. |
| Security Admin (`security`) | Security, impersonation, data. |
| AI Admin (`ai`) | AI governance. |
| Support (`support`) | Tickets, health, impersonation requests. |
| Auditor (`auditor`) | Read-only audit/evidence. |

### External actors
Candidates, BGV vendors, job boards, banks, statutory portals (EPFO/ESIC/Income Tax/PT), identity providers (SSO), payment gateways, AI/LLM providers, video & calendar providers, e-sign providers.

## 11.3 Organizational hierarchy (data ownership)

```
Platform Operator
  └── Tenant (company)               ← billing, entitlement, residency boundary
        └── Legal entity / Establishment   ← statutory registration (PF/ESI/PT codes)
              └── Location (work site)      ← shift defaults, holiday calendar, geofence
                    └── Department
                          └── Designation / Band / Grade
                                └── Employee  ← reporting_manager, skip_level
```

**Data ownership rules (derived):**
- Tenant is the hard isolation boundary; no cross-tenant data access (except platform operator via audited impersonation).
- Employee owns their self-service submissions; manager owns approvals for their reports; HR owns master data; Finance owns payroll/statutory; IT owns assets/access.
- Statutory filings are owned at the **establishment** level, consolidated calendar-monthly across pay groups.

## 11.4 Access levels & RBAC requirements

- **BR-RBAC-1** Access is role + scope: a role grants capabilities; scope (self/team/department/location/establishment/tenant) bounds the data set.
- **BR-RBAC-2** Approver must not equal requester (segregation of duties) — `[M]`, required for SOX/SOC2.
- **BR-RBAC-3** Field-level masking for sensitive PII (salary, PAN, Aadhaar, bank) based on role — `[M]`.
- **BR-RBAC-4** Platform operator access to tenant data requires an approved, time-boxed, audited impersonation session with data masking — `[D]` in control plane.
- **BR-RBAC-5** Delegations transfer approval authority for a bounded type & window; accountability remains with the principal — `[D]`.

## 11.5 Approval hierarchy

Approvals are configured, not coded (`WORKFLOW_ROUTING`). Standard chains observed:

| Process | Chain | Gating |
|---------|-------|--------|
| Leave | Manager → (HR for special types) | balance, blackout, notice |
| Advance | HR direct (skips manager for emergency) | amount cap |
| Bank change | HR only | security |
| Requisition | Hiring Mgr → BU Head → Finance → HR | budget/headcount |
| Offer | Recruiter → HRBP → Finance → BU Head | comp band, budget |
| Compensation | 5 escalation tiers by ₹ threshold | amount |
| Asset request | Manager → IT → Finance → Procurement | cost, policy |
| Timesheet | PM → Manager | project, billable |
| Cost-center spend | tiered by amount | budget |
| Payroll run | Maker → Finance approve → disbursement | reconciliation |
| F&F | HR verify → Finance verify → Payroll approve | clearance, recoveries |
| Exit | Manager → Retention (if regrettable) → HR | notice, dues |
| Performance increment | Manager → Calibration → HR/Finance | budget, band |
| Compliance pack (platform) | Legal → sandbox → impact → approve → publish | acknowledgement |

## 11.6 Workflow hierarchy (process layer)

The **macro lifecycle** chains module workflows: `Requisition ▸ Offer ▸ BGV ▸ Onboarding ▸ (employee active) ▸ recurring [Attendance ▸ Leave ▸ Timesheet ▸ Payroll] ▸ Performance cycle ▸ Exit ▸ F&F`. Each macro step triggers the next (e.g. offer accepted auto-triggers BGV; Day-1 issues employee identity; increment approval feeds payroll; exit clearance feeds F&F recoveries).

## 11.7 Reporting requirements

- **BR-RPT-1** Pre-built reports across 9 module-aligned categories (35 definitions observed).
- **BR-RPT-2** Filters: period, department, location; export Excel/PDF/CSV/email.
- **BR-RPT-3** Scheduled delivery (active/paused) to recipients.
- **BR-RPT-4** Self-service custom report builder with AI suggestions.
- **BR-RPT-5** Statutory registers & returns: PF ECR, ESIC, PT, 24Q, Form 16/12BA, muster, wage register `[M]`.
- **BR-RPT-6** Cross-module analytics: attrition (Pulse), headcount, cost-to-company, utilization, time-to-fill.

## 11.8 Non-functional requirements

| ID | NFR | Target (derived) |
|----|-----|------------------|
| NFR-1 | Multi-tenancy | Thousands of tenants, hard isolation. |
| NFR-2 | Scale | Millions of employees; largest tenant 10k+; payroll for 10k in < 10 min. |
| NFR-3 | Availability | 99.9%+ (control plane has uptime tracking & status). |
| NFR-4 | Data residency | Region-pinned per tenant (India/EU/US). |
| NFR-5 | Security | SSO/SAML, MFA, encryption at rest/in transit, secrets vault, IP allowlists. |
| NFR-6 | Auditability | Immutable, tamper-evident audit; 7-yr retention. |
| NFR-7 | Compliance | DPDP Act (India), GDPR (EU), SOC2; statutory currency via packs. |
| NFR-8 | Performance | P95 interactive < 300ms; async for heavy compute (payroll, reports). |
| NFR-9 | Extensibility | New modules added without core changes; public API + webhooks. |
| NFR-10 | DR | Defined RPO/RTO; periodic DR tests (control plane models DR tests). |

## 11.9 Key business rules (consolidated, cross-module)

1. **One identity end-to-end.** A person has exactly one identity that begins as a candidate and becomes an employee at Day-1; portal and ESS share it. No re-entry of profile/docs across the boundary.
2. **Module gating.** A tenant only sees modules its plan entitles; UI and API both enforce.
3. **Calendar-month statutory consolidation.** Statutory dues consolidate establishment-wide across pay groups into one ECR/ESIC/PT filing per month.
4. **Recoveries flow to F&F.** Outstanding asset/loan/advance/notice/bond recoveries auto-populate exit F&F.
5. **Increment feeds payroll.** Approved performance increments bridge into the next payroll structure.
6. **OOD/WFH is duty pre-approval, not leave.** WFH/OOD migrated out of leave types into the OOD module and auto-create attendance.
7. **Amount-gated escalation.** Financial approvals escalate by configurable ₹ thresholds.
8. **Compliance is governed data.** Statutory rates & rules are centrally versioned, impact-analysed, and published; tenants acknowledge.
9. **SLA on every approval.** Each request type has an SLA with approaching/breach behaviour.
10. **Delegation ≠ transfer of accountability.** Acting approver is recorded; principal remains accountable.

## 11.10 Assumptions & constraints

- Primary market **India** first (currency ₹, FY Apr–Mar, PF/ESI/PT/TDS); design is i18n/multi-currency aware for expansion.
- The prototype encodes intent; all server, persistence, compute, and integration behaviour is to be built (see gap analysis).
- Pricing PEPM implies accurate active-employee metering is revenue-critical.
