# Module: Payroll, Statutory, Tax, Assets, Finance & Exit/F&F

> Reverse-engineered from `atvantiq-people-prototype_2.html` (28,238 lines). All field names, enums, statuses and labels below are quoted verbatim from the source JS. Line refs are approximate.

---

## Screen-by-Screen Audit

### 1. Payroll (`SCREENS.payroll`, ~13124)
- **Purpose:** Run-cycle hub for a pay month. Tabbed shell over 7 sub-views.
- **Actors:** Payroll Admin / HR / Finance (persona-gated; module hidden if persona lacks access).
- **Tabs (`pay-views`):** `run` Run cycle · `statutory` Statutory & compliance · `payslips` Payslips · `advances` Advances · `taxdecl` Tax declarations · `bank` Bank & disbursement · `settings` Settings. Dispatched via `PAY_VIEWS[payView]()`.
- **Header:** title "Payroll"; sub "`${PAY_MONTH.label}` cycle · 248 employees · cutoff in 3 days"; month prev/next buttons (`‹ May 2026`, `Jun 2026 ›`).
- **Cross-module banner:** "₹ N approved increments from Performance & Growth" card listing `PERF_INCREMENTS` where `status==='approved' && !pushed_to_payroll` — columns Employee/Rating/Current/Revised/Inc/Effective; button **→ Push to Payroll** (`perfPushToPayroll()`).
- **Modals rendered globally:** `renderCompModal`, `renderStructModal`, `renderAdvanceModal`.
- **Dependencies:** `EMPLOYEES_MASTER`, `TA_PENALTIES`, `OT_PENDING`, `ATTENDANCE_DAY_APPROVALS`, `REGULARIZATIONS`, `LEAVE_REQUESTS`, `LEAVE_BALANCES`, `PERF_INCREMENTS`, statutory masters.

### 1a. Run cycle (`PAY_VIEWS.run`, ~13622; group select via `selectPayGroup`)
- **Purpose:** Pay-group overview → per-group run with a 5-stage state track.
- **Inputs:** `PAY_GROUPS` (cal/mid/twelfth), `payGroupSelected`, `payStage`, `payHeld`, attendance & leave bridges.
- **UI:** Pay-group cards (name, period, employees, note). Inside a group: "← All pay groups" back button; group label strip; **interactive status track** `pay-status-track` over `PAY_STAGE_ORDER=[draft,preview,approved,bankfile,paid]` (dots clickable only for stages ≤ current); stage action button (right) — Download preview (preview only) + a primary advance button whose label depends on stage (`stageAction` map below). Body = `PAY_STAGE[payStage]()`.
- **Stage action labels:** draft→"Lock inputs & generate preview"; preview→"Approve & lock"; approved→"Proceed to bank file"; bankfile→"Mark as disbursed"; paid→"Close cycle". On paid: green "✓ Complete" pill.
- **Preview stage body (`PAY_STAGE.preview`):** T&A impact strip (`✓ ready/total ready`, total LOP days, OT, pending approvals from `attendancePayrollSummary()`); KPI tiles (count, gross, basic, net, employer cost = `gross*0.137`, held count/net); full register table from `PAY_REGISTER` (cols: employee, dept, monthly gross, LOP days, present, basic, hra, special, pf, pt, tds, esi, net, bank, anomaly badges); per-row **Hold** action (`openHoldModal`/`confirmHold`/`releaseHold`); anomaly chips (e.g. "LOP 8 days", "Reimbursement 2x", "Inactive").
- **Hold modal:** asks for optional reason; toast "Employee held · Excluded from this run · release anytime before lock".
- **Business rules:** Active = `gross>0 && !payHeld`. Held employees excluded from totals. Employer cost ≈ 13.7% of gross. Stage can only move forward via `advancePayStage`; backward clicks allowed to any prior stage. Entering `bankfile` auto-switches `payView` to `bank`.

### 1b. Statutory & compliance (`PAY_VIEWS.statutory`, ~14232)
- **Purpose:** Calendar-month, establishment-wide statutory consolidation across pay groups.
- **Key rule (verbatim):** "Statutory filings are calendar-month and establishment-wide — independent of pay cycles. All pay groups disbursed in May roll up into one ECR, one ESIC challan, one PT return."
- **UI:** AI banner with consolidated headcount; filing-deadline tiles — EPF·ECR (Due 15 Jun, EPFO), ESIC (15 Jun), TDS deposit (7 Jun, monthly), PT·by state (20 Jun); pay-group rollup table (cols: pay group, pay period, disbursed, employees, EPF, ESIC, PT, TDS, run status — Locked/Paid) attributed by **disbursement month**; consolidated establishment totals row.
- **Dependencies:** `groupRollup` placeholder data; `STATUTORY_RATES`.

### 1c. Payslips (`PAY_VIEWS.payslips`, ~14391)
- **Purpose:** Per-employee payslip listing/preview (payslip layout driven by `SAL_COMPONENTS.onPayslip`).

### 1d. Advances (`PAY_VIEWS.advances`, ~13324)
- **Purpose:** Salary-advance register; issue, request, recover from salary.
- **Inputs:** `ADVANCES`, `ADV_PURPOSES`, filter `advFilterStatus` (all/requested/active/paid_off/rejected), schedule engine `computeAdvanceSchedule`.
- **UI:** Status filter chips; advance cards/rows (employee, amount, balance, purpose, method, interest, status pill, monthly deduction, months paid/remaining, perquisite); **+ New / Request** opens `renderAdvanceModal`. Modal inputs: employee, amount, purpose, method (lump/tenure/installment/custom), tenure, installment, lump month, interest method (none/flat/reducing), rate; live schedule preview (month/payment/interest/principal/balance).
- **Business rules:** Perquisite tax when amount > `perquisite_threshold` (₹20,000) valued at SBI PLR (`sbi_plr_pct` 8.5%); interest methods: none=0, flat=`principal*rate/1200*N`, reducing=EMI. Statuses: requested→active→paid_off, or rejected.

### 1e. Tax declarations (`PAY_VIEWS.taxdecl`, ~14513; modal ~14863)
- **Purpose:** Per-employee per-FY investment declaration + HR review + proof verification.
- **Inputs:** `TAX_DECLARATIONS`, `TENANT_TAX_CONFIG`, `STATUTORY_RATES`.
- **Filters:** FY, status (all/submitted/approved/draft/proof_pending/missing), regime (all/new/old), dept.
- **Table:** employee, regime, status pill, declared deductions, computed taxable income / annual tax / monthly TDS. "Not filed" rows for employees with no declaration.
- **Modal (`renderTaxdeclModal`):** two modes — `hr` (review, read-only when approved/finalized) and `ess` (employee edit). Sections: regime toggle; HRA (rent_monthly, metro, landlord_pan); 80C breakdown with cap warning (`sec_80c_cap` ₹1.5L, shows over-cap & effective); 80CCD(1B), 80CCD(2); 80D (self_family, parents, senior, preventive); 80E/80G/80TTA; home loan interest (cap `sec_24b` ₹2L); LTA planned; previous employer (name/income/tds/pf); other income (rental/capital_gains/interest/dividend); proofs (submitted_at/verified). Button **Approve declaration** → toast "TDS schedule activated".
- **Lifecycle:** draft → submitted → approved → proof_pending → finalized.

### 1f. Bank & disbursement (`PAY_VIEWS.bank`, ~14655)
- **Purpose:** Choose routing strategy and generate bank disbursement files.
- **Inputs:** `COMPANY_ACCOUNTS`, `payRouting` (single/custom), `payRoutingAccount`, `payCustomRules`.
- **UI:** Routing cards (Single account / Custom split). Single → account chips (primary badge, masked acct). Custom → per-account rule rows: rule type (Priority fill / Remaining catch-all), "prefers <bank> employees first", cap by (amount/count), cap value, remove (✕), **+ Add account rule**; coverage banner ("N of M employees assigned"; warns if no Remaining account). Disbursement files table (source account, bank·format, routing, employees, mode NEFT, amount); **Generate N files** button.
- **Rules:** Priority fill takes own-bank employees first (free/instant) then others up to cap; Remaining sweeps the rest. Must have a Remaining account to cover everyone.

### 1g. Payroll Settings (`PAY_VIEWS.settings`, ~15097; also Settings overlay `paySetSection`)
- **Sections (`paySetSection`):** salary | groups | bank | cycle | statutory. Dispatched by `PAY_SET_SECTION` registry.
  - **salary** → `renderSalConfig`: tabs Components / Structures.
  - **bank** → `renderBankAccountsSetting` (~9521): manage `COMPANY_ACCOUNTS`.
  - **statutory** → `renderStatutoryRates` (~9573): view/edit `STATUTORY_RATES` + history.

### 2. Salary Configuration — Components tab (`renderComponentsTab`, ~5212; modal `renderCompModal`)
- **Purpose:** Component library CRUD. Table cols from `SAL_COMPONENTS`: code, name, type (`COMP_TYPE_LABEL`), calc (`CALC_LABEL`), value, tax (`TAX_LABEL`), PF wage, ESI wage, gratuity base, PT, LWF, FBP, pro-rata LOP, on payslip, active.
- **Component modal fields:** all `SAL_COMPONENTS` keys editable; type select (earning/deduction/reimbursement/employer); calc select (fixed/pct_basic/pct_ctc/pct_gross/balancing/slab/computed/formula); tax select (taxable/partial/exempt); boolean toggles.

### 3. Salary Configuration — Structures tab (`renderStructuresTab`, ~5253; modal `renderStructModal`)
- **Purpose:** Structure templates bundling components, mapped to band/grade/location, with live CTC preview (`structPreviewCTC` default 1,200,000).
- **Table from `SAL_STRUCTURES`:** name, band, grade, location, basic %, hra %, component count, employees, active.

### 4. Assets (`SCREENS.assets`, ~23447) — multi-tab module
Tabs (`assetsTab`): dashboard, registry, requests, allocations, inventory, maintenance, licenses, access, audit, lost, depreciation. Persona-gated `ops-assets`.

- **4a. Registry (`renderAssetRegistry`):** Full `ASSETS` table — filters cat/status; cols id, category, brand/model, serial/IMEI/MAC/QR, owner, location, status pill (`assetStatusColor`), condition, finance tag, book value. Drawer (`assetDrawerSection`) with overview. Action **Mark for repair** (`assetMarkRepair` → status `Under Repair`, creates repair record).
- **4b. Requests (`renderAssetRequests`):** `ASSET_REQUESTS` pipeline (`ASSET_REQ_STAGES`). Stage pills via `assetReqStageColor`; per-stage approve/reject (`assetReqAdvance`/`assetReqReject`). Cols id/type, requester, reason, category, mgr, SLA due, priority.
- **4c. Licenses (`renderAssetLicenses`):** `ASSET_LICENSES` — name, vendor, plan, seats, assigned, renewal, cost, dept, compliance pill (`licenseComplianceColor`: compliant/underutilised/expiring/overused).
- **4d. Access management (`renderAccessManagement`):** `ACCESS_PROFILES` × `ACCESS_SYSTEMS` matrix; state pills `provisioned/pending/revoked/not-applicable` (`accessStateColor`). Provision/deprovision toggles.
- **4e. Audit (`renderAssetAudit`):** `ASSET_AUDITS` — name, scope, dates, progress %, verified, mismatch, pending, status (in_progress/closed).
- **4f. Maintenance (`renderAssetMaintenance`):** `ASSET_REPAIRS` (`REPAIR_STATUSES`); cols asset, issue, reported by/on, vendor, warranty, temp asset, cost, downtime days, status pill (`repairColor`).
- **4g. Lost/incidents (`renderAssetLost`):** `ASSET_INCIDENTS` — asset, employee, date, condition (Lost/Damaged), orig value, book value, recovery, waiver, linked exit, deduction status (`incidentDeductionColor`: pending_finance/approved/deducted/waived). **Approve** (`incidentApprove`) flows recovery to F&F.
- **4h. Integrations:** `ASSET_INTEGRATIONS` (M365, Google Workspace, Slack, Teams, GitHub, Jira, Zoho, Tally/SAP/Oracle/QuickBooks, ServiceNow, Freshservice, QR scanner) with connected/sync/last.
- **4i. Depreciation (`renderAssetDepreciation`, ~23997):** see Finance/Asset screen below.

### 5. Asset Finance / Depreciation (`SCREENS['finance-asset']`, ~24032 → `renderAssetDepreciation`)
- **Persona:** `finance-asset` / `assets-depreciation` (Finance / Super Admin only).
- **UI:** KPI tiles — Purchase value, Accumulated depreciation (cost−book), Net book value, Capex/Opex count. Per-asset table: asset, finance tag pill (Capex/Opex), dep method, purchase date, cost, book value, vendor, invoice. Actions **→ Push to ERP** (Zoho Books), **↓ Export** depreciation report.
- **Rule (verbatim):** "No full accounting ledger here — this prepares export data only. Connect Zoho Books / Tally / SAP in Settings → Integrations to auto-sync." Dep methods on assets: `SLM 33%/yr`, `SLM 25%/yr`, `SLM 20%/yr`, `SLM 50%/yr`, `Expensed`. Settings note SLM/WDV configured in Settings → Finance → Depreciation.

### 6. Cross-module Recoveries (`SCREENS['finance-recoveries']`, ~24036)
- **Persona:** `finance-asset`.
- **Purpose:** Aggregate recoveries from `ASSET_INCIDENTS` (asset damage/loss) + `EXIT_CASES` notice shortfall buyouts.
- **UI:** KPI tiles (open recoveries count, total value, pending approval count). Table: Source pill (Asset/Notice shortfall), subject, employee/dept, amount, status pill, linked record (click → exit case or assets/lost). **↓ Export** CSV.

### 7. Asset Purchase Approvals (`SCREENS['finance-purchases']`, ~24067)
- **Persona:** `finance-asset`.
- **Purpose:** Finance approval queue for `ASSET_REQUESTS` at stage `finance_approval`.
- **Rule:** "Asset purchases above the configured threshold require Finance sign-off. Below threshold, IT can fulfil directly."
- **UI:** Queue table (request id/type, requester, reason, category) with **Approve** (`assetReqAdvance`) / **Reject** (`assetReqReject`).

### 8. Exit & F&F (`SCREENS.exit`, ~24260) — full lifecycle module
- **Sidebar phases (`EXIT_NAV`):** Overview (Dashboard/Analytics) · Exit Process (Resignations/Retention/Notice) · Offboarding (KT/Clearance/Exit Interview) · Settlement & Closure (F&F/Documents/Alumni-Rehire).
- **Header action:** **+ Initiate exit** (`taOpenForm('exit-initiate')`).
- **8a. Dashboard (`renderExitDashboard`):** AI Exit Pulse tiles; KPI bento — Active exits, Resignations (May), Pending mgr approvals, Pending clearances, Pending F&F, Avg F&F settlement (38d), Regrettable attrition, High-risk exits (regrettable & `ai_score>=70`). Active exits table (employee, dept, reason, stage pill, LWD, regrettable).
- **8b. Resignations (`renderExitResignations`):** Pipeline strip over `EXIT_PIPELINE` with per-stage counts; case rows.
- **8c. Retention:** retention play form (`exit-retention`); AI retention score & suggested action.
- **8d. Notice:** notice period, served/shortfall, buyout, garden leave, early release (`exit-early-release` form).
- **8e. KT (`renderExitKT`):** checklist (6 items), replacement, shadow/reverse-shadow; actions `exitOpenKt`, `exitApproveKt`.
- **8f. Clearance (`renderExitClearance`):** per-dept rows (Manager/HR/IT/Admin/Finance/Assets) with owner, SLA, status (`exitClearanceColor`), remarks, recovery; actions `exitClearDept`, `exitWaiveDept`, form `exit-clearance`. Recovery amounts auto-flow into F&F.
- **8g. Exit interview (`renderExitInterview`):** form `exit-interview`; AI summary (primary/secondary/sentiment/risk/action), category ratings, rehire eligibility.
- **8h. F&F (`renderExitFnf` + `renderFnfStatement`, ~24578):** payslip-style settlement (Earnings vs Recoveries vs Statutory vs Net). Table (employee, LWD, gross, recoveries, net payable, pay date, stage). Negative net = employee owes company (routed to recovery). Actions **Download statement** (PDF placeholder), **Approve & advance** (`exitAdvanceFnf`), Locked state.
- **8i. Documents (`renderExitDocuments`):** doc master (10 docs); per-case status (generated/pending), approved_by, e-sign; **Generate / Generate all** (`exitGenerateDoc`/`exitGenerateAllDocs`), PDF/Email actions.
- **8j. Alumni (`renderExitAlumni`):** alumni cards with rehire eligibility, cooling period, referral, skills; **Add to talent pool** (`exitToTalentPool`), Invite to alumni network.
- **8k. Analytics (`renderExitAnalytics`):** attrition intelligence (spikes, manager risk, comp-driven, high-performer alerts).

---

## Entities (Data Model)

### PAY_MONTH (~4940)
`{label, totalDays, weekends, holidays, workingDays}` — current run context (placeholder; LOP formula = totalDays − weekends − holidays − lopDays; pro-rate = monthlyGross/totalDays × payableDays).

### PAY_GROUPS (~5575)
`{id, name, period, start, end, employees, note}` — cal (1st–last, 198), mid (16–15, 38), twelfth (12–11, 12).

### PAY_REGISTER (~4943) — array tuples
`[id, name, initials, color, dept, monthlyGross, lopDays(ATT), present(ATT), basic, hra, special, pf, pt, tds, esi, net, bank, anomaly[]]`.

### COMPANY_ACCOUNTS (~4911) — array tuples
`[id, label, bank, accountNo, ifsc, beneficiary, mode(NEFT), isPrimary]`.

### payCustomRules / payRouting (~4918)
Rule `{accountId, ruleType(priority|remaining), capKind(count|amount), capValue}`; `payRouting` = single|custom.

### payHeld (~4871)
`{ empId: reasonText }` — manually-held employees for current run.

### SAL_COMPONENTS (~5141)
`{id, code, name, type(earning|deduction|reimbursement|employer), calc(fixed|pct_basic|pct_ctc|pct_gross|balancing|slab|computed|formula), calcValue, tax(taxable|partial|exempt), pfWage, esiWage, gratuityBase, ptApplicable, lwfApplicable, isFBP, proRataLOP, onPayslip, active}`.
Seeded: basic, hra, special, da(inactive), conveyance, cea, lta, meal, telecom, books, fuel, epf_ee, pt, tds, esi_ee, epf_er, esi_er, gratuity, bonus.
Label maps: `COMP_TYPE_LABEL`, `CALC_LABEL`, `TAX_LABEL` (~5175).

### SAL_STRUCTURES (~5168)
`{id, name, band, grade, location, basicPct, hraPct, components[], employees, active}` — std_l3, std_l4, senior, ops_field.

### STATUTORY_RATES (~5905) — platform master, effective-dated
- `epf{employee_pct:12, employer_pct:12, eps_pct:8.33, eps_wage_cap:15000, eps_amount_cap:1250, edli_pct:0.5, edli_wage_cap:15000, edli_amount_cap:75, admin_charges_pct:0.5, admin_charges_min:500, pf_wage_ceiling:15000, effective_from}`
- `esi{employee_pct:0.75, employer_pct:3.25, wage_threshold:21000, disability_threshold:25000, contribution_period_1:'Apr–Sep', contribution_period_2:'Oct–Mar'}`
- `tax_slabs_new` (6 slabs 0/5/10/15/20/30), `tax_slabs_old` (4 slabs), `tax_slabs_senior_old` (60-80), `tax_slabs_super_senior_old` (80+)
- `std_deduction{new:75000, old:50000}`, `rebate_87a{new:{700000,25000}, old:{500000,12500}}`
- `surcharge[]` (10/15/25/37%), `surcharge_new_cap:25`, `cess_pct:4`
- `sec_80c_cap:150000`, `sec_80ccd_1b_cap:50000`, `sec_80d_self_cap:25000`, `sec_80d_senior_cap:50000`, `sec_24b_self_occupied_cap:200000`
- `hra_metro_cities[]`
- `gratuity{accrual_pct_monthly:4.81, exemption_cap:2000000, eligibility_years:5}`
- `bonus{eligibility_wage_threshold:21000, computation_salary_cap:7000, min_pct:8.33, max_pct:20}`
- `sbi_plr_pct:8.5`, `perquisite_threshold:20000`

### STATUTORY_RATES_HISTORY (~5993)
`{field, from, to, effective_from, by, note}`.

### TENANT_TAX_CONFIG (~6003)
`{current_fy, declaration_window{open,deadline}, proof_window{open,deadline}, default_regime:'new', allow_regime_switch_mid_year:false, auto_apply_default:true, send_reminders, reminder_days_before_deadline[14,7,3,1]}`.

### TAX_DECLARATIONS (~6017)
`{id, empId, fy, regime(old|new), status(draft|submitted|approved|proof_pending|finalized), submittedAt, reviewedBy, reviewedAt, finalizedAt, hra{rent_monthly,metro,landlord_pan}, sec80c{epf_employee,ppf,elss,lic,tuition,home_loan_principal,nsc,ulip}, sec80ccd_1b, sec80ccd_2, sec80d{self_family,parents,parents_senior,preventive_health}, sec80e, sec80g, sec80tta, home_loan_interest, lta_planned, prev_employer{name,income,tds,pf}, other_income{rental,capital_gains,interest,dividend}, proofs{submitted_at,verified,verified_by,reminder_sent}, computed{taxable_income,annual_tax,monthly_tds}}`.

### ADV_PURPOSES / ADVANCES (~13162)
`{id, empId, empName, empInit, empColor, amount, balance, purpose, method(lump|tenure|installment|custom), tenure, installment, lumpMonth, interestMethod(none|flat|reducing), rate, status(requested|active|paid_off|rejected), startMonth, issuedOn, issuedBy, requestedBy, requestedOn, rejectedBy, rejectedOn, rejectedReason, closedOn, monthlyDeduction, monthsPaid, monthsRemaining, perquisiteApplicable, perquisitePerMonth}`.

### COST_CENTERS (~7074)
`{id, code, name, type(operational|profit|service), parent_id, owner_id, department_id, legal_entity, geo, budget_year, budget_amount, budget_currency, budget_period, actual_spent, committed, status(active|frozen), is_rollup, notes}` — hierarchical tree (root → Eng/Ops/GTM trees + frozen Legacy US).
### CC_APPROVAL_TIERS (~7102)
`{below, approver_role, label}` — <50k cc_owner; 50k–5L finance_head; 5L–50L cfo; >50L ceo_and_cfo.

### ASSETS (~23360)
`{id, cat, type, brand, model, serial, imei, mac, qr, purchase_date, cost, vendor, invoice, warranty_start, warranty_end, amc_vendor, amc_expiry, location, dept, owner, owner_name, status, condition, finance_tag(Capex|Opex), dep_method, book_value, remarks}`.
`ASSET_CATEGORIES[15]`, `ASSET_STATUSES[10]` (Available/Reserved/Allocated/In Transit/Under Repair/Returned/Lost/Damaged/Disposed/Written Off).

### ASSET_REQUESTS (~23375)
`{id, type, asset_cat, requester, requester_name, reason, submitted, stage, mgr, sla_due, priority}`.
`ASSET_REQ_STAGES`=[draft, manager_review, it_approval, finance_approval, procurement, fulfilled, acknowledged]; `ASSET_REQ_STAGE_LABEL`.

### ASSET_LICENSES (~23386)
`{id, name, vendor, plan, seats, assigned, renewal, cost, dept, compliance(compliant|underutilised|expiring|overused)}`.

### ACCESS_SYSTEMS / ACCESS_PROFILES (~23401)
`{empId, name, role, systems:{<system>: provisioned|pending|revoked|not-applicable}}` over 10 systems.

### ASSET_AUDITS (~23410)
`{id, name, scope, start, end, progress, verified, mismatch, pending, status(in_progress|closed)}`.

### ASSET_REPAIRS (~23416)
`{id, asset, asset_name, issue, reported_by, reported_on, vendor, warranty, temp_asset, cost, downtime_d, status, resolution}`; `REPAIR_STATUSES`=[reported, under_review, sent_to_vendor, repaired, replaced, closed].

### ASSET_INCIDENTS (~23423)
`{id, asset, asset_name, employee, employee_name, date, condition, orig_value, book_value, recovery, waiver, linked_exit, deduction_status(pending_finance|approved|deducted|waived)}`.

### ASSET_INTEGRATIONS (~23429)
`{key, name, category, connected, sync, last}`.

### EXIT_CASES (~24115)
`{id, name, emp_id, init, avatar_color, dept, sub, manager, grade, location, doj, resignation_date, notice_days, proposed_lwd, confirmed_lwd, reason, exit_type(Voluntary|Involuntary|Retirement|Absconding|Contract End), regrettable, retention_prob, status,`
- `retention{perf_rating, tenure_y, comp_percentile, critical_skills[], project_dependency, replacement_difficulty, ai_score, suggested_action, attempted, outcome}`
- `notice{policy_days, served_days, shortfall, buyout_amount, garden_leave, early_release}`
- `kt{status(not_started|in_progress|submitted|manager_review|approved), projects, clients, open_tasks, pending_tickets, docs_handed, replacement, shadow, reverse_shadow, checklist[{k,done}]}`
- `clearance[{dept, owner, sla, status(pending|in_progress|cleared|blocked|recovery|waived), remarks, recovery}]`
- `interview{done, would_rejoin, would_recommend, rehire_eligible, categories[{cat,rating}], ai_summary{primary,secondary,sentiment,risk,action}}`
- `fnf{status, earnings{salary_lwd,leave_encash,bonus,variable,arrears,gratuity,notice_pay}, recoveries{notice,asset,loan,advance,bond,excess_salary}, statutory{pf,esi,pt,tds,gratuity}, net{gross,recoveries,tax,net_payable,pay_date,mode,utr}}`
- `documents[{name, status, approved_by, signed}]`
- `alumni{email, phone, linkedin, last_desig, skills[], new_company, rehire_eligibility, cooling_period, remarks, referral_allowed}` }`
- `EXIT_NAV`, `EXIT_PIPELINE`, `EXIT_STAGE_LABEL`, `EXIT_FNF_FLOW`.

---

## Payroll Engine
- **Component model:** each `SAL_COMPONENTS` row carries calc type + per-component statutory inclusion flags (pfWage, esiWage, gratuityBase, ptApplicable, lwfApplicable) + tax treatment + isFBP + proRataLOP + onPayslip. Calc types: `fixed`, `pct_basic`, `pct_ctc`, `pct_gross`, `balancing` (remainder/special-allowance plug), `slab` (PT), `computed` (TDS engine), `formula` (custom). Tax: taxable/partial(HRA,CEA,LTA)/exempt.
- **Sequencing/balancing:** Basic=50% CTC; HRA=40% Basic; Special=balancing remainder; FBP/reimbursements fixed; statutory deductions computed; employer contributions (EPF-ER 12%, ESI-ER 3.25%, gratuity 4.81%, bonus 8.33%) off-payslip.
- **Structures:** bundle components, map band/grade/location, basicPct/hraPct, live CTC preview.
- **Pay groups:** different cutoff cycles (cal/mid/twelfth); each group run independently.
- **Run state machine:** `draft → preview → approved → bankfile → paid` (`PAY_STAGE_ORDER`). Forward via `advancePayStage`; can jump back to any prior stage; bankfile auto-switches to disbursement tab. Active = gross>0 && not held; employer cost ≈ 13.7% of gross.
- **Holds:** `payHeld` excludes employees from the run with optional reason; releasable before lock.
- **Attendance/Leave bridges:** `computeAttendancePayrollImpact` (LOP from absent + late-penalty tiers + OT), `computeLeavePayrollImpact` (paid vs LOP leave, encashable EL for F&F); readiness gating (`readyForPayroll` blocked by pending approvals/regularizations).
- **Bank file generation:** routing single/custom (priority fill by own-bank + remaining catch-all), one file per source account; coverage validation requires a Remaining account.

## Statutory & Tax
- **PF/ESI/PT/Gratuity/Bonus:** full rate master in `STATUTORY_RATES` (effective-dated, platform-synced, with change history). EPF wage ceiling 15k, EPS cap 1250, EDLI cap 75, admin 0.5%/min 500. ESI thresholds 21k/25k, contribution periods Apr–Sep / Oct–Mar. Gratuity 4.81%/mo, 5-yr eligibility, ₹20L exemption. Bonus 8.33–20%, cap salary 7k.
- **Tax regimes:** old vs new slab tables + senior/super-senior old; std deduction (75k/50k); 87A rebate; surcharge tiers + new-regime cap 25%; cess 4%; deduction caps (80C 1.5L, 80CCD(1B) 50k, 80D 25k/50k, 24b 2L). Default regime `new`; mid-year switch disallowed; auto-apply default if not filed.
- **Declaration lifecycle:** draft → submitted → approved → proof_pending → finalized. Declaration window + proof window per FY; reminders at 14/7/3/1 days. HR review (read-only post-approval) + ESS edit modes; 80C over-cap warning; proof verification (`proofs.verified`, verified_by).
- **Statutory filing:** calendar-month, establishment-wide consolidation across pay groups (one ECR / ESIC challan / PT return); attributed by disbursement month; deadlines EPF/ESIC 15th, TDS 7th, PT 20th.

## Assets & Access
- **Registry lifecycle:** statuses Available→Reserved→Allocated→In Transit→Under Repair→Returned/Lost/Damaged→Disposed/Written Off. Each asset has warranty/AMC, finance tag, dep method, book value.
- **Request approval chain:** draft → manager_review → it_approval → finance_approval → procurement → fulfilled → acknowledged. Finance gate above threshold; below, IT fulfils directly.
- **Licenses:** seat tracking + compliance (compliant/underutilised/expiring/overused).
- **Access provisioning:** matrix of profiles × systems with provisioned/pending/revoked/not-applicable; integrations (M365/Google/Slack/Teams/GitHub/Jira) for auto sync.
- **Repairs:** reported → under_review → sent_to_vendor → repaired/replaced → closed; temp asset, warranty, downtime.
- **Audits:** quarterly / location / self-verification with progress, verified/mismatch/pending.
- **Incidents:** Lost/Damaged → recovery flow (pending_finance → approved → deducted/waived), linked to exit → F&F.
- **Depreciation:** SLM (33/25/20/50%/yr) or Expensed; WDV configurable in Settings; export-only (no internal ledger), pushes to Zoho Books/Tally/SAP.

## Exit & F&F
- **Pipeline:** draft → submitted → manager_review → retention_review → accepted → notice_period → lwd_confirmed → exited. Voluntary regrettable exits route through retention_review (`exitApprove`).
- **Phases:** Resignation → Retention (AI score + play) → Notice (served/shortfall/buyout/garden leave/early release) → KT (6-item checklist, shadow/reverse-shadow) → Clearance (6 depts, recovery capture) → Exit Interview (AI summary, rehire eligibility) → F&F → Documents → Alumni/Rehire.
- **F&F computation:** Earnings (salary till LWD, leave encashment, bonus, variable, arrears, gratuity, notice pay) − Recoveries (notice shortfall, asset, loan, salary advance, training bond, excess salary) − Statutory (PF, ESI, PT, TDS, gratuity tax) = Net payable (negative = employee owes company → recovery, not payout). UTR captured on payment.
- **F&F flow:** draft → hr_verified → finance_verified → payroll_approved → payment_processed → paid → closed (`EXIT_FNF_FLOW`, `exitAdvanceFnf`).
- **Documents (10):** Resignation acceptance, LWD confirmation, No dues, Relieving, Experience, Service certificate, F&F statement, Gratuity letter, PF withdrawal guide, Exit summary — generation + approval + e-sign + email (all placeholder/toast).

---

## State Machines
1. **Payroll run:** `draft → preview → approved → bankfile → paid` (forward-only advance, backward jump allowed, bankfile→disbursement tab).
2. **Asset request:** `draft → manager_review → it_approval → finance_approval → procurement → fulfilled → acknowledged` (reject → draft).
3. **Exit pipeline:** `draft → submitted → manager_review → retention_review → accepted → notice_period → lwd_confirmed → exited`.
4. **F&F flow:** `draft → hr_verified → finance_verified → payroll_approved → payment_processed → paid → closed`.
5. **Tax declaration:** `draft → submitted → approved → proof_pending → finalized`.
6. **Advance:** `requested → active → paid_off` (or `rejected`).
7. **Repair:** `reported → under_review → sent_to_vendor → repaired/replaced → closed`.
8. **Incident recovery:** `pending_finance → approved → deducted` (or `waived`).
9. **Clearance (per dept):** `pending → in_progress → cleared` (or `blocked`/`recovery`/`waived`).

---

## Feature Inventory (this module)
- **Payroll run:** pay-group cycles, 5-stage interactive run track, register with anomaly detection, per-employee hold/release, attendance & leave bridges, OT, employer-cost estimate.
- **Salary engine:** component library (8 calc types, 3 tax types, statutory flags), structure templates with live CTC preview.
- **Statutory:** effective-dated rate master + history, calendar-month establishment-wide consolidation, filing deadline tracker.
- **Tax:** old/new regime config, full declaration form (HRA/80C/80CCD/80D/80E/80G/80TTA/24b/LTA/prev-employer/other-income), HR review + proof verification, computed TDS schedule.
- **Advances/Loans:** lump/tenure/installment/custom methods, flat/reducing interest, schedule engine, perquisite handling.
- **Bank disbursement:** single/custom routing, priority-fill + remaining rules, multi-account file generation.
- **Assets:** registry, request approval chain, licenses, access provisioning matrix, audits, repairs, incidents/recoveries, integrations, depreciation/ERP export.
- **Cost-center finance:** hierarchical CCs with budgets/rollups, tiered approval matrix.
- **Finance lenses:** cross-module recoveries, purchase approval queue, asset depreciation.
- **Exit & F&F:** retention AI, notice/buyout, KT, 6-dept clearance, exit interview, F&F settlement statement, document generation, alumni/rehire.

---

## Gaps (Missing but Required)
1. **Payslip PDF generation** — `onPayslip` flags & payslips tab exist but no actual PDF render/download engine (toasts only). Employees need statutory-compliant payslips.
2. **Form 16 / 24Q / TDS returns** — TDS computed per-employee but no Form 16 issuance, no quarterly 24Q e-TDS return generation/filing. Required for compliance.
3. **Real TDS computation engine** — `calc:'computed'` and `computed.monthly_tds` are pre-seeded; no actual engine applying slabs/rebate/surcharge/cess to projected annual income net of declarations.
4. **Bank file format/integration** — files are listed but no real NEFT/RTGS/H2H file format (e.g. HDFC/ICICI fixed-width/XML), no bank API, no UTR reconciliation back into the register.
5. **GL / accounting posting** — depreciation & payroll are export-only; no double-entry GL, no journal vouchers, no cost-center-wise salary posting. ERP push is a toast.
6. **Arrears / retro pay** — `arrears` appears only in F&F; no retroactive recompute when increments (from Performance) apply mid-cycle or structures change.
7. **PF/ESI return files (ECR/challan)** — consolidation totals shown but no ECR text file, ESIC contribution file, or PT challan generation per state.
8. **Reconciliation & variance controls** — anomaly chips are static; no bank-vs-register reconciliation, no prior-month variance audit trail, no maker-checker on F&F beyond a single advance button.
9. **Depreciation schedule computation** — `book_value` is hardcoded; no period-by-period WDV/SLM schedule, no accumulated-depreciation roll-forward, no disposal gain/loss.
10. **LWF / labour-welfare-fund & per-state PT slabs** — `lwfApplicable` flag and PT `slab` calc exist but no actual LWF rates or state-wise PT slab master (Karnataka/Maharashtra etc.).
