# 13 — Workflow Documentation

Each workflow is described as a state machine (states + transitions + actors + guards + side-effects). Side-effects in **bold** are cross-module triggers. Sources are the `*_STAGES`/`*_PIPELINE`/`*_FLOW` enums and routing config in the prototype.

## 13.0 The generic approval engine (foundation)

All approvals are instances of this engine (`WORKFLOW_ROUTING`):

```
SUBMIT ─► [step 1] ─► [step 2] ─► … ─► APPROVED
            │ reject       │ reject
            ▼              ▼
         RETURNED       REJECTED
```
- **Step resolution**: each step targets `reporting_manager | skip_level | department_head | management | hr_manager | finance | company_admin | specific_person | designated_pool`.
- **Mode**: `any` (one approver suffices) or `all` (every approver must approve).
- **Amount gating**: financial requests insert extra escalation steps when amount ≥ tier threshold (compensation: 5 tiers).
- **SLA**: `slaHrs` on `slaBasis` (business/calendar); at `approachingPct` → reminder; at breach → `reminder | escalate | visual | auto_finalize`.
- **Snapshot** `[M]`: routing is snapshotted at submit so later config changes don't alter in-flight cases.
- **Delegation**: if an approver has an active delegation for this type/window, the delegate acts; principal remains accountable.
- **Side-effects**: every transition emits an **audit event** and **notification**.

---

## 13.1 Hire-to-onboard macro flow (TA)

```
Workforce plan ─► Requisition ─► Sourcing ─► Candidate pipeline ─► Interviews ─► Offer ─► BGV ─► Pre-board ─► Day 1 ─► Onboarding ─► Probation ─► Confirmed
```

### Requisition
`draft → pending(HiringMgr) → pending(BU Head) → pending(Finance) → pending(HR) → open → (filled | on_hold | cancelled)`
- Guards: budget/headcount available. **Side-effect on fill**: decrement headcount `[M]`.

### Candidate pipeline (per candidate)
`applied → screening → interview → offer → bgv → preboard → onboarding → probation → confirmed` · terminal: `rejected | dropped`
- `offer accepted` → **auto-trigger BGV**; `bgv cleared` → **unlock Day-1**; `Day 1` (`taSimulateDay1`) → **issue employee identity (ESS)**; `90-day confirm` → `confirmed`.

### Offer
`draft → pending(Recruiter) → pending(HRBP) → pending(Finance) → pending(BU Head) → released → (accepted | declined | expired)`
- Guard: within comp band/budget. `accepted` → **BGV + candidate portal unlock**.

### BGV
`initiated → consent_captured → checks_running(9 types) → results → adjudication(Recruiter → HRBP → Compliance) → (clear | discrepancy | fail)`
- Vendor API integration; consent & retention required `[M]`.

### Onboarding
Template-driven tasks across owners (HR/IT/Admin/Manager/Employee) with per-task SLA; learning gate; e-sign documents. Completion → employee fully active.

### Probation
`active → (30/60/90 checkpoints) → (confirmed | extended | terminated)`. Should hard-gate on review + learning + BGV `[M]`.

---

## 13.2 Recurring operations (active employee)

### Attendance day approval
`captured(multi-source) → reconciled → pending_l1(Manager) → pending_l2(Reviewer) → finalized` · auto-finalize on SLA breach.
- Override path: `ATTENDANCE_OVERRIDES` log with reason.

### Regularization
`raised(type: missing_in/out, wrong_time, face_failed, gps_failed) → pending(approver per config) → (approved → attendance corrected | rejected)`.

### Overtime
`detected → pending(Manager) → (approved | rejected)` or auto-approve per policy. **Side-effect**: approved OT → payroll OT input `[M]`.

### Leave
`draft → pending(Manager) → [pending(HR) for ML/PAT/special] → (approved | rejected | cancelled)`
- Guards: balance ≥ requested, blackout, notice period, sandwich rule `[M]`. **Side-effect**: approved leave → attendance + payroll LOP/encashment input `[M]`.
- Special cases: bereavement auto-approve (6h); advance skips manager (emergency); bank-change HR-only.

### Comp-off
`earned(extra-day work) → ledger credit → claim → pending(Manager) → (approved → leave-equivalent | expired)`.

### OOD / WFH
`requested → pending(Manager) → (approved → auto-create attendance as on-duty | rejected)`.

### Timesheet
`draft → submitted → pm_approved(PM) → approved(Manager) → (locked | reopened)` with period freeze. **Side-effect**: approved billable → invoice input `[M]`; cost-center actuals update.

### Cost-center spend
`requested → tiered approval by amount (CC_APPROVAL_TIERS) → (approved | rejected)`; updates budget/actual/committed.

---

## 13.3 Payroll run

`draft → preview → approved → bankfile → paid`
- `draft`: gather inputs (attendance LOP, OT, leave encashment, advances, increments, declarations).
- `preview`: compute earnings/deductions/employer cost/TDS; variance vs last month; holds (`payHeld`).
- `approved`: maker-checker sign-off (Finance).
- `bankfile`: generate bank file → auto-switch to disbursement tab.
- `paid`: mark paid, UTR reconciliation `[M]`, **generate payslips** `[M]`, **GL posting** `[M]`, **statutory filing inputs** (ECR/ESIC/PT/24Q) `[M]`.
- Backward jump to any prior stage allowed (re-run).

### Tax declaration (feeds payroll)
`open(FY) → submitted(employee, regime old/new) → proof_pending → verified(HR/Finance) → locked` → drives TDS projection.

### Advance / loan
`requested → pending(HR) → (active → installment schedule → paid_off | rejected | cancelled)`. **Side-effect**: installments deducted in payroll; outstanding → F&F recovery.

---

## 13.4 Asset & access

### Asset request
`draft → manager_review → it_approval → finance_approval → procurement → fulfilled → acknowledged`
- **Side-effects**: allocation updates registry; **access provisioning** on systems; incident damage → **recovery → F&F**.

### Asset repair
`reported → under_review → sent_to_vendor → (repaired | replaced) → closed`.

### Asset incident
`reported → assessed → (recovery raised → F&F) → closed`.

---

## 13.5 Exit & Full-and-Final

### Exit pipeline
`draft → submitted → manager_review → retention_review(if regrettable) → accepted → notice_period → lwd_confirmed → exited`
- Parallel tracks once accepted: **KT**, **clearance** (assets/IT/finance/HR), **access deprovisioning** `[M]`.

### Clearance (per department)
`pending → in_progress → cleared` (or `dues_pending → recovery`). All clearances → enable F&F.

### F&F settlement
`draft → hr_verified → finance_verified → payroll_approved → payment_processed → paid → closed`
- Compute: `Earnings(salary till LWD, leave encashment, bonus, variable, arrears, gratuity) − Recoveries(notice shortfall, asset, loan, advance, bond, excess salary) − Statutory(PF, ESI, PT, TDS, gratuity tax) = Net`.
- If Net < 0 → **employee owes → recovery**. **Side-effect**: generate F&F statement, relieving/experience/service letters, no-dues `[M]`.

---

## 13.6 Performance review cycle

`draft → goal_freeze → self_review → manager_review → reviewer_review → calibration → final_rating → increment → outcome_release → closed`
- `goal_freeze`: lock goals/OKRs.
- `self_review` (employee) → `manager_review` (manager) → `reviewer_review` (HOD).
- `calibration`: forced curve (15/25/50/8/2 advisory) + 9-box placement.
- `increment`: input increment/promotion → **bridge to payroll** (`perfPushToPayroll`).
- `outcome_release`: publish ratings/letters.

### PIP
`draft → active → checkpoint_due → (improved | extended | closed | termination_recommended)`
- 3 auto-checkpoints; `termination_recommended` → **feed exit** `[M]`.

---

## 13.7 Control-plane workflows

### Tenant lifecycle
`trial → active → attention → suspended → archived` · provisioning (DB/region/entitlements) → activation → billing.

### Compliance pack publish
`draft → legal_review → sandbox_preview → impact_analysis → approved → published → acknowledged → archived`
- **Side-effect**: published pack updates tenant statutory rates; tenants must acknowledge; evidence bundle retained.

### Feature flag / release rollout
`off ⇄ on/beta` with targeting + rollout % + prerequisites; `kill` halts; rings stage exposure (Internal→Alpha→Beta→Early Access→Stable→Enterprise Locked→Custom).

### Impersonation
`pending_approval → (active → completed | denied)` with mandatory data masking + full audit + time-box.

### Invoice / billing
`draft → issued → (paid | overdue → dunning | disputed → resolved | refunded)`; metering → invoice generation.

### Integration health
`healthy ⇄ paused | error → retry → (recovered | failed)`; webhooks emit on tenant events.

---

## 13.8 Notification matrix (who gets told, on what)

| Event | Recipients | Channels |
|-------|-----------|----------|
| Request submitted | Approver(s) | in-app, email |
| SLA approaching | Approver | in-app, email, reminder |
| SLA breach | Approver + escalation target | email, escalate |
| Approved/rejected | Requester | in-app, email |
| Delegation active | Delegate + principal | in-app |
| Payroll preview ready | Finance | in-app, email |
| Payslip published | Employee | in-app, email |
| Offer released | Candidate | email, portal |
| BGV discrepancy | Recruiter, Compliance | in-app, email |
| Probation due | Manager, HR | in-app, email |
| Exit accepted | HR, IT, Finance (clearance) | in-app, email |
| Compliance pack published | Tenant admins | in-app, email, ack-required |
| Integration failed | Platform ops, tenant admin | email, webhook |

(Engine to be built — see `12-gap-analysis.md` G-F4.)
