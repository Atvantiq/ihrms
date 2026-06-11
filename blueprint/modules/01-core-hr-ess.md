# Module: Core HR, ESS & Platform Plumbing

> Reverse-engineered from `atvantiq-people-prototype_2.html` (28,238 lines). All field names, labels,
> statuses and enums below are quoted verbatim from the JS object literals and render functions.
> Owned screens: **dashboard, tasks, directory, profile (Employee 360), ess, candidate-portal**, plus the
> cross-cutting persona/role/workflow/SLA/delegation plumbing and the Settings → Workflows & Approvers panes.

---

## Screen-by-Screen Audit

### 1. Dashboard (`SCREENS.dashboard`, line 1669)
- **Purpose:** Company Admin / IT landing. AI-prioritized "inbox of decisions" plus headline KPI bento tiles.
- **Actors:** Default for `company` role; persona `it`/`hr`/`super`/`manager`/`finance` (employees redirect to ESS, finance to `finance-asset`).
- **Inputs:** None (static seeded). **Outputs:** navigation deep-links to other screens.
- **UI Elements:**
  - Page head: title "Good morning, Rohit", subtitle "5 things waiting on you"; buttons **This week**, **+ New action**.
  - **HERO AI Inbox tile** ("Atvantiq AI · Inbox", "5 decisions ready · sorted by urgency", ⌘K button). 5 inbox cards: Payroll anomalies (danger→payroll), Attrition risk 78% (warn→pulse), Candidates passed AI screen (→recruiting), 3 leave requests pending >24h (→leave), Probation ends in 6 days (→onboarding). Each card: icon, title, sub, action label, severity color (`danger`/`warn`/''), nav target.
  - KPI tiles: **Headcount** 248 (▲12 this month · 4 leaving); **Open roles** 14 (5 in review · 38 active candidates); **May payroll · preview** ₹38.4L gross (stacked bar Net/Statutory/Tax); **Today · attendance** 94% (233 of 248; bar In/Late/WFH/Leave); **Hiring funnel · this month** (Sourced 142 / Screened✦ 38 / Interview 17 / Offer 5 / Joined 3, →recruiting); **Celebrations** card (birthdays + work anniversaries with avatars, "6 more this month").
- **Business Rules:** Inbox sorted by urgency; severity drives left-border/badge color. **Permissions:** company-role default; redirect logic in `togglePersona()`.
- **Dependencies:** payroll, pulse, recruiting, leave, onboarding screens.

### 2. Tasks / Inbox (`SCREENS.tasks`, line 8267)
- **Purpose:** Unified approvals + requests workspace across every "hat" the user holds (dual-role UX: Rohit = Company Admin + HR Manager + Manager, who also has his own manager Sneha).
- **Actors:** All personas. Role filter chips: **All hats / As Manager / As HR / As Me**.
- **Inputs:** `TASKS[]`, derived ESS/exit/asset/perf pending lists. **Outputs:** approve/reject mutate both Task and source record (bidirectional resolution, comment in `§BIDIRECTIONAL RESOLUTION`).
- **UI Elements:**
  - 3 **tabs**: `awaiting_me` (badge red if SLA-breached, else warn), `by_me`, `all` — counts `{awaiting, byMe, all, urgent}`.
  - **Role filter** buttons (all/manager/hr/employee), **Type filter** pills built from `REQUEST_GROUPS` (all, leaves, ood_wfh, attendance, salary, lifecycle, profile, asset) with per-group counts; empty groups hidden.
  - **AI SLA banner** (only when urgent>0) naming the longest-pending breaches.
  - **`renderApprovalsInbox()`** consolidated card "Approvals awaiting you" with rows from: ESS pending (`essActOnRequest` approve/reject), exit resignations (`exitApprove`/`exitReject`), KT signoffs (`exitApproveKt`), asset requests (`assetReqAdvance`/`assetReqReject`), perf self/manager/calibration reviews, PIP checkpoints, promotions. Each row: type pill, title, detail+approver, action buttons.
  - **Task cards** (`renderTaskCard`): type icon/color chip, type label, **role badge**, skip-level badge ("↑ Skip-level (via X)" when requester not a direct report), "On behalf of" badge, completion pill (✓ Auto-accepted / ✓ Approved / ✕ Rejected), SLA badge, requester+summary, "Submitted X", "N of M steps complete", inline Reject/Approve.
  - **Empty state**: "Inbox zero ✓".
  - **Delegation footer hint** when an active/scheduled delegation exists.
  - **Task Detail Modal** (`renderTaskDetailModal`): Request details grid (Requester+id, Submitted+timeAgo, Type, Amount, Summary), "Open full advance record →" when `refId`, **Approval chain** stepper (done=green ✓ circle else number; step label, by·at·decision), comment textarea ("visible in audit trail and to requester"), foot actions Cancel/Reject/Approve.
  - **Delegate Modal** (`renderDelegateModal`): see Workflows.
  - **Bell dropdown** (`renderBellDropdown`): top-5 awaiting, SLA-breach highlight, "Open Tasks workspace →".
- **Business Rules:** `tasksAwaitingMe/ByMe/All/Urgent` derive lists; `isTaskVisible` hides `feature_gated:'attendance_approval'` tasks when `ATTENDANCE_APPROVAL_CONFIG.enabled` is false. `by_me` includes completed where `myRole∈{employee,hr_initiator}`. Skip-level computed from `EMPLOYEES_MASTER[requesterId].managerId !== CURRENT_USER.id`.
- **Validation:** none beyond comment optional. **Permissions:** every persona sees tasks for the hats they hold (filter chips).
- **Dependencies:** ESS_REQUESTS, EXIT_CASES, ASSET_REQUESTS, PERF_*, WORKFLOW_ROUTING, REQUEST_TYPES, EMPLOYEES_MASTER, DELEGATIONS, payroll advances.

### 3. People / Directory (`SCREENS.directory`, line 15345)
- **Purpose:** Workforce directory list with filters, stats, bulk ops, per-row actions.
- **Actors:** HR/IT/manager/super (people lifecycle).
- **UI Elements:**
  - Page head: "People", "12 of 248 employees · 8 departments · 5 locations"; **+ Add employee** (`openAddEmployee`); ⋮ menu → **Bulk import** (`openBulkImport`), **Export** submenu (Export all / Export current view), **Download import template** (Atvantiq-People_template.xlsx), **Manage columns**.
  - **AI Smart search ribbon** (natural-language examples, "Open ⌘K →").
  - **Filter bar:** search input (name/ID/email), selects: **All departments** (Engineering 84 / Operations 62 / Sales 38 / People 14 / Finance 12), **All locations** (Bengaluru 180 / Pune 42 / Hyderabad 18 / Remote 8), **All status** (Active 218 / Probation 12 / Joining 3 / Notice 6 / Inactive 9 / Exited). Match count.
  - **Stats row** (5 tiles): Active 218, Probation 12, Joining 3, On notice 6, Inactive 9.
  - **Employee table** columns: ☑ | Employee (avatar+name+email) | Emp ID | Designation | Department | Location | Manager | Tenure | Status (pill with `title` reason) | ⋯ row menu. Row click → profile.
  - **Row ⋯ menu:** Edit profile, Open profile, **Generate letter** submenu (Offer / Appointment / Experience / Address proof / Salary certificate / Appreciation / Promotion / Compensation revision / Warning / Show-cause / Termination notice / Custom letter via AI), Initiate comp review, Issue salary advance (`openAdvanceModal`), Mark inactive (`openMarkInactive`), **Initiate exit**.
  - **Pagination** ("Page 1 of 21", Prev/Next, page chips).
- **Status enum (directory):** `Active`, `Probation`, `Joining`, `Notice`, `Inactive`, `Exited` (status colors green/warn/blue/warn/ghost). Each row carries a human reason (e.g. "resigned 30 Apr · last day 30 Jun", "on maternity leave · returns 12 Aug").
- **Business Rules:** status computed (see Profile status-card). **Dependencies:** profile, advance modal, exit flow, bulk import.

### 4. Employee 360 / Profile (`SCREENS.profile`, line 15535)
- **Purpose:** Full 360° employee record with grouped tabs + sub-tabs and a customizable-fields editor.
- **Actors:** HR/IT/manager/super; employee sees own subset via ESS.
- **UI Elements:**
  - **Top tabs (`PROFILE_TABS`):** Overview, Job & comp (`job`), Personal, Documents, Time & growth (`time`), Assets, Compliance, Activity. Plus **Quick-switch** ("Switch to another employee…", ⌘P) and **Customise fields** (caption editor `openCaptionEditor`).
  - **Hero** (shared): avatar, "Mrs. Priya Sharma · ATV-0142", designation/dept/location, status pills (● Active, "3y 4m tenure", "Reports to Sneha A.", "2 direct reports", "L4 · Grade B2"); actions **Message**, **Org chart ↗**, **✎ Edit profile** (`openEditEmployee`), ⋮ menu (Generate letter submenu identical to directory, Initiate comp review, Issue salary advance, Schedule 1:1, Mark inactive, Initiate exit).
  - **Status card:** auto-computed status reasoning (Active ← joined+probation cleared+no resignation; transitions to **Notice** on resignation, **Inactive** on manual pause/long-leave/sabbatical/suspension).
  - **Overview tab:** Identity field-group (Salutation, Full name, Father's/Mother's name, DOB, Blood group, Sex, Marital status, Spouse name, Nationality, Languages known, Qualification, Driving licence, Reference); Contact (Email, Mobile, Alternate phone, Personal email + Present/Permanent address cards); Statutory IDs (PAN, Aadhaar masked, UAN, ESI number, Passport number/issued-at/issued/expires); Recent activity list; **Manager brief** AI tile; Quick actions; Leave balance (Paid/Sick/Casual); Remarks.
  - **Job & comp tab:** Position grid (Designation, Band/level L4, Grade B2, Department, Sub-dept, Division, Manager, Skip-level, Direct reports, Branch, Work mode, Employment, Salary structure, Attendance, DoJ, Salary calc. from); **Band & market** percentile slider; **Statutory configuration** (PF applicable, PF number, PF no for dept file, Restrict PF cap ₹1800, Zero pension/skip EPS, ESI applicable, ESI number, ESI dispensary, Zero PT exempt, Ward/circle, Director flag); **CTC structure** (CTC ₹14,40,000; tiles Annual CTC / Monthly gross / Monthly take-home / Cost to company; breakdown bar; 4 tables — Earnings fixed, Flexible benefits FBP, Deductions employee, Employer contributions; each row label/rule/monthly/annual); **Tax regime comparison** Old vs New; **Compensation history** table (Date, Event, From, To, Change, Approved by); **Salary advances** section (active recovery cards with progress, history table, +Issue advance); **Tax declaration card** (`renderTaxDeclSectionForEmployee`).
  - **Personal tab:** **Family & Nominees** table (Name, Relation, Remarks, DOB, Dependent, Nominee, Address, Share %); Nomination-check AI tile; **Special dates** table (Description, Remarks, Date, Yearly, Payslip option); **Other details** table (Description, Comments, Date).
  - **Documents tab:** Document vault grouped by category (KYC / Contract / Education / Experience / Letters / Compliance); each doc: category, name, file, size, status pill, Download; drag-drop upload card (PDF/DOC/JPG max 10MB); **Expiring soon** (Passport, Visa); Generate-letter AI tile.
  - **Time & growth tab** (`TIME_SUB`): sub-tabs **Attendance / Leave & T&A / Performance / Training / Education**. Attendance deep-dive (May stats present/late/half_day/wfh/leave/absent/ot_hrs/hours_worked/avg_check_in, shift, recent events, pending regularizations/OT).
  - **Compliance tab** (`COMPLIANCE_SUB`): sub-tabs **Disciplinary / Accidents / Extra curricular / Awards**. Disciplinary (memos/PIPs, "retained 7 years post-exit"); Accidents (Factories-Act/ESIC); Sports & events table.
  - **Activity tab**, **Assets tab** (asset registry view).
- **Business Rules:** status auto-computed; tax-decl status machine (see Enums); leave year-end action via `yearEndAction()`. **Dependencies:** ADVANCES, TAX_DECLARATIONS, LEAVE_BALANCES, ATTENDANCE_EVENTS, shifts/regularization, EMPLOYEES_MASTER.

### 5. Self-service / ESS (`SCREENS.ess`, line 25008)
- **Purpose:** Employee web portal (default `essView='portal'`; mobile preview toggle). Demo employee = Anita Sharma (ATV-0203).
- **Actors:** Employee persona (own data only).
- **UI Elements — tabs** (`renderEssPortal`): **Home, Attendance & Time, Leave & OOD, Payroll & Tax, Claims, My Assets, My Requests** (badge=pending count), **My Profile, Performance**.
  - **Home:** KPI tiles (Today In·09:30 WFH, Leave balance total, This month attendance 96%, Pending requests); Attendance punch card (Punch out); **Quick actions grid** (`essQuickActions`): Apply leave, Regularize, Overtime, WFH/OOD, Claim expense, Salary advance, Tax declaration, Update details; Company updates/newsletter (`ESS_ANNOUNCEMENTS`); My recent requests.
  - **Attendance:** This month stats; Quick log actions; **Needs your attention · regularization** table (from `ESS_REGULARIZE`); Recent attendance log (Date/In/Out/Hours/Source/Status; statuses present/short/wfh).
  - **Leave & OOD:** Leave balances from `LEAVE_BALANCES` × `LEAVE_TYPES_CONFIG`; Apply leave / WFH-OOD; Leave & OOD history table.
  - **Payroll & Tax:** Tax & documents actions (Submit tax declaration, Download Form 16, Apply salary advance, View salary structure); Year-to-date tiles (Gross paid, TDS, Net paid, 80C declared); **Payslips** table (`ESS_PAYSLIPS`: Month, Gross, Deductions, Net pay, Status=paid, view·PDF).
  - **Claims:** AI explainer (OCR pre-fill); Pending vs Approved-YTD totals; File a claim; Claims table (`ESS_CLAIMS`: Category, Description, Date, Amount, Receipt, Status).
  - **My Assets:** assigned assets (acknowledge/report-issue), software & licenses, my access, open asset requests.
  - **My Requests:** consolidated `ESS_REQUESTS` table (Type, Request, Submitted, With, Decided, Status).
  - **My Profile:** Personal + Contact & bank (masked) + My documents; **Request a change** (`ess-profile-edit`, routes to HR).
  - **Performance:** current cycle, goals, last rating, My goals (OKRs) table, Feedback & 1:1s.
- **ESS request forms** (`TA_FORM_SCHEMAS` via `Object.assign`): `ess-leave`, `ess-regularization`, `ess-ot`, `ess-wfh`, `ess-reimbursement`, `ess-advance`, `ess-tax`, `ess-profile-edit` — each with fields, note, and `onSubmit` that unshifts into `ESS_REQUESTS`/`ESS_CLAIMS` with status `pending` and routes to manager/Finance/HR/Payroll. (See Entities for field lists.)
- **Business Rules:** balance auto-deducted on leave approval; conflicts with team leave flagged; advance EMIs auto-deducted; sensitive field changes (bank/name) need HR/document verification; tax declaration feeds TDS/Form 16. **Permissions:** employee sees only own records.
- **Dependencies:** LEAVE_BALANCES, LEAVE_TYPES_CONFIG, ASSETS, ACCESS_PROFILES, ASSET_REQUESTS, ATTENDANCE_SOURCES, Tasks inbox (approvals reflect back).

### 6. Candidate Portal (`SCREENS['candidate-portal']`, line 3438)
- **Purpose:** Candidate-facing surface — **same login as ESS, separate surface**; progressive unlock. Opens at **offer acceptance**, collects BGV consent/docs, unlocks Day-1 details once BGV clears, then **hands off to ESS on Day 1** (single identity).
- **Actors:** Candidates in stages `offer (accepted) / bgv / preboard / onboarding / probation / confirmed`.
- **UI Elements:** explainer tile; **candidate selector** chips (preview-as); body = `renderTaPreboardPortal()` (days-to-DOJ countdown, doc collection with statuses verified/uploaded/pending, e-signs Offer/NDA signed) OR `renderPortalHandoff()` (Joined → ESS). Phase label: Pre-boarding / BGV in progress / Cleared to join / Joined → ESS.
- **Business Rules:** offer-stage candidate gets portal only when `offer.status==='accepted'`; `TA_JOINED[c.id]` or stage∈{onboarding,probation,confirmed} ⇒ joined ⇒ ESS handoff.
- **Dependencies:** TA_CANDIDATES, offers, BGV cases, ESS (carry-over identity). *(Recruiting/BGV detail owned by TA module.)*

### 7. Settings → Workflows & Approvers (panes, registered line 8686+)
- **Purpose:** Configure approval routing, SLA, roles, designations, delegations.
- **Panes:** `workflows` (Workflows & routing), `approvers` (Approvers & roles), spliced into `SETTINGS_CATS[0]` (Workspace). Also Roles & permissions (`roles`), Notifications (`notifications`).
- **UI Elements:** business-hours/days config (TENANT_SLA_CONFIG), per-request-type workflow editor (`renderWorkflowEditModal`), role cards (`renderRoleCard`), assignee chips, **Approver edit modal**, **Role editor modal** (`renderRoleEditorModal`: Role name*, Description, Icon picker `ROLE_ICON_LIBRARY`, Scoping cards flat/department/project, "Used in workflows" usage, Delete guarded by usage). **Settings categories** (`SETTINGS_CATS`): Workspace, Modules, Talent Acquisition, Performance & Growth, Exit & F&F, Assets & IT, Finance, Integrations, Personal — full item list in Feature Inventory.

---

## Entities (Data Model)

### PERSONAS (line 1263) — company-side RBAC demo personas
Array of: `key` (enum: `employee`|`manager`|`it`|`finance`|`hr`|`reviewer`|`super`), `label`, `dot` (color var), `desc`. Mutable `currentPersona` (default `it`). `personaHas(feature)` maps feature→allowed personas (super always true).

### SA_ROLES (line 1324) — platform Super-Admin roles
`key` (enum: `owner`|`ops`|`release`|`compliance`|`billing`|`security`|`ai`|`support`|`auditor`), `label`, `dot`, `desc`. `saRole` default `owner`; `applySaRoleVisibility` gates `data-sa-role` nav.

### CURRENT_USER (line 5697)
`id` (ATV-0023), `name`, `initials`, `color`, `title`, `managerEmpId`, `managerName`, `roles[]` (`['Company Admin','HR Manager','Manager']`).

### REQUEST_TYPES (line 5705) — 19 request flow types (map keyed by type)
Keys: `leave, advance, comp, expense, ood, exit, asset, profile, bank, declaration, regularization, ot, attendance_day, comp_off, ml, pat, bereavement, marriage, wfh`. Each: `label`, `icon`, `color`.

### REQUEST_GROUPS (line 5730) — 8 filter buckets
`key`, `label`, `icon`, `includes[]` (type keys). Keys: `all, leaves, ood_wfh, attendance, salary, lifecycle, profile, asset`. `requestGroupFor(typeKey)` resolves.

### WORKFLOW_ROUTING (line 5748) — per-type routing config (mutable)
Keyed by request type. Each: `steps[]` (each step: `roles[]` (role keys), `mode` `any`|`all`, optional `condition` string e.g. `'amount > 100000'`, optional `autoRecord`), `slaHrs` (int), `slaBasis` (`business_days`|`calendar`), `approachingPct` (int), `onBreach` (`reminder`|`escalate`|`visual`|`auto_finalize`), `reminderIntervalHrs`, `notificationChannels[]` (`email`/`sms`/`whatsapp`), optional `note`.

### ROLE_CATALOG (line 5850) — approver role definitions (mutable)
Keyed by role key. Fields: `label`, `scope` (`auto`|`designated`|`specific`), `scopedBy` (`auto`|`flat`|`department`|`project`|`specific`), `icon`, `desc`, `editable` (bool), `builtIn` (bool), `system` (bool, optional).
Built-in keys: `reporting_manager, skip_level_manager, department_head, management, hr_manager, finance, company_admin, specific_person`. Seeded custom: `it_team, compliance_officer, project_manager`.

### ROLE_DESIGNATIONS (line 5878) — who fills each designated role (mutable)
Shape depends on `scopedBy`: **flat** = `[empId]`; **department** = `{deptKey:[empId]}`; **project** = `{projectId:[empId]}`. Helpers `roleAssigneeCount`, `roleAllAssignees`, `workflowsUsingRole`.

### PROJECTS (line 5867)
`id, name, dept, status` (`active`|`planning`), `startDate, endDate (nullable), desc`.

### EMPLOYEES_MASTER (line 7797) — org-chart master (keyed by empId)
`name, init, color, title, dept` (enum from DEPARTMENTS), `managerId` (nullable, self-referential FK).

### DEPARTMENTS (line 7812)
`['engineering','sales','operations','finance','people-ops']`.

### TENANT_SLA_CONFIG (line 7862)
`businessHoursStart, businessHoursEnd, businessDays[]` (mon..fri), `timezone` (Asia/Kolkata), `defaultApproachingPct`. `slaPreview()` renders human text.

### NOTIFICATION_CHANNELS (line 7885)
`key` (`email`|`sms`|`whatsapp`), `label`, `icon`.

### DELEGATIONS (line 7892) — outgoing delegations (mutable)
`id, toEmpId, toName, toInit, toColor, types[]` (request type keys), `startDate, endDate, reason, status` (`scheduled`|`active` [+ revoked implied]).

### TASKS (line 7902) — seeded inbox items
`id, type` (REQUEST_TYPES key), `requesterId, requesterName, requesterInit, requesterColor, summary, amount` (optional), `submittedAt, hoursAgo, slaHrs, slaBreached` (bool), `status` (`awaiting_me`|`by_me`|`completed`), `myRole` (`hr`|`manager`|`employee`|`hr_initiator`), `resolution` (optional: `approved`|`rejected`|`auto_accepted`|`settled`), `approvalChain[]` (each: `step, by, at, done` bool, optional `decision`), optional `refId`, optional `feature_gated` (`attendance_approval`).

### LEAVE_TYPES_CONFIG (line 6588) — leave policy master (mutable, 13 types)
Per type: `key, label, code, icon, color, description, consumes_balance, is_paid, is_attendance_marker?, deprecated?, affects_payroll?`,
`accrual{method` (`monthly`|`annual_upfront`|`event_based`|`earned`|`unlimited`)`, annual_entitlement, monthly_rate, pro_rate_for_new_joiners, qualifying_period_days}`,
`carry_forward{enabled, max_days, expiry_after_months}`,
`encashment{enabled, on_separation, during_employment, max_per_year}`,
`application{min_advance_notice_days, max_consecutive_days, half_day_allowed, sandwich_applies, requires_medical_after_days, requires_doc, blackout_applies, max_per_month?, location_required?}`,
`eligibility{probationers, gender` (`all`|`male`|`female`)`, after_months}`, `active, show_in_ess`.
Types: el, cl, sl, ml, pat, comp_off, bereavement, marriage, wfh(deprecated), ood(deprecated), lop.

### LEAVE_BALANCES (line 6704) — per-employee per-type balances
Keyed by empId → `{leaveKey:{accrued, used, available, carryFwd}}`.

### ESS_REQUESTS (line 24908)
`id, type` (`leave`|`regularization`|`ot`|`reimbursement`|`wfh`|`advance`|`tax`), `title, detail, submitted, status` (`pending`|`approved`|`rejected`), `approver, decided (nullable)`.

### ESS_CLAIMS (line 24916)
`id, category, amount, date, desc, status` (`pending`|`approved`), `receipt` (bool).

### ESS_PAYSLIPS (line 24921)
`month, gross, deductions, net, status` (`paid`).

### ESS_ANNOUNCEMENTS (line 24928)
`tag` (Newsletter/Policy/Event), `title, body, date, color`.

### ESS_REGULARIZE (line 24934)
`date, issue, canRequest` (bool).

### ESS form schemas (TA_FORM_SCHEMAS additions, line 24944)
- `ess-leave`: type(select←LEAVE_TYPES), from, to, reason → ESS_REQUESTS(leave, →Sneha).
- `ess-regularization`: date(select←ESS_REGULARIZE), actual_in, actual_out, reason(select).
- `ess-ot`: date, hours(number), comp(Comp-off|Overtime pay), reason.
- `ess-wfh`: mode(WFH|OOD), from, to, reason.
- `ess-reimbursement`: category, amount, date, desc, receipt → ESS_CLAIMS + ESS_REQUESTS(→Finance).
- `ess-advance`: amount, months(1-6), reason → (→Finance).
- `ess-tax`: regime, section, amount, proof → (→Payroll).
- `ess-profile-edit`: field(Phone|Address|Emergency contact|Bank account|Marital status), value → (→HR).

### Profile sub-structures (mutable rendered tables)
- **Family & Nominees:** Name, Relation, Remarks, DOB, Dependent (Yes/No), Nominee (Yes/No), Address, Share %.
- **Special dates:** Description, Remarks, Date, Yearly, Payslip option.
- **CTC tables:** Earnings/FBP/Deductions/Employer (label, rule, monthly, annual).
- **Compensation history:** Date, Event, From, To, Change, Approved by.
- **Documents:** category, name, file, size, status, color.
- **Statutory config flags:** PF applicable, PF number, PF dept file no, Restrict PF (cap ₹1800), Zero pension, ESI applicable, ESI number, ESI dispensary, Zero PT, Ward/circle, Director flag.

### Supporting platform masters (referenced, owned/detailed elsewhere)
STATUTORY_RATES (5905, EPF/ESI/tax-slabs/gratuity/bonus), TENANT_TAX_CONFIG (6003), TAX_DECLARATIONS (6017), ATTENDANCE_APPROVAL_CONFIG (6441), REGULARIZATION_CONFIG (6523).

---

## Enums & Status Machines

- **Persona:** employee | manager | it | finance | hr | reviewer | super.
- **SA role:** owner | ops | release | compliance | billing | security | ai | support | auditor.
- **Request type (19):** leave, advance, comp, expense, ood, exit, asset, profile, bank, declaration, regularization, ot, attendance_day, comp_off, ml, pat, bereavement, marriage, wfh.
- **Task.status:** `awaiting_me → (approve|reject) → completed`; `by_me` (own submissions); `completed`.
- **Task.resolution:** approved | rejected | auto_accepted | settled | recorded.
- **ESS request status:** `pending → approved | rejected` (decided date stamped on decision via `essActOnRequest`).
- **ESS claim status:** pending → approved (rejected implied).
- **Directory/Profile employee status (auto-computed):** `Joining → Probation → Active`; `Active → Notice` (resignation); `Active → Inactive` (manual pause/long-leave/sabbatical/suspension); `Notice → Exited`.
- **Tax declaration status:** Not filed → draft → submitted → approved → proof_pending → finalized.
- **Advance status:** active | paid_off | rejected.
- **Delegation status:** scheduled | active | (revoked).
- **Workflow.onBreach actions:** reminder | escalate | visual | auto_finalize.
- **Workflow step mode:** any | all. **slaBasis:** business_days | calendar.
- **Role scope:** auto | designated | specific. **scopedBy:** auto | flat | department | project | specific.
- **Candidate portal phase:** offer(accepted) → bgv → preboard → onboarding → probation → confirmed → (Joined→ESS).
- **Leave accrual method:** monthly | annual_upfront | event_based | earned | unlimited.
- **Document status:** verified | uploaded | pending | signed.

---

## Workflows

Routing = ordered `steps[]`; each step resolves `roles` (auto from org chart, designated from `ROLE_DESIGNATIONS`, or specific person), `mode` any/all, optional conditional gate. SLA tracked per `slaHrs`/`slaBasis`; `approachingPct` triggers "approaching" state; `onBreach` action fires; reminders every `reminderIntervalHrs` via `notificationChannels`.

- **leave:** L1 Reporting manager (any) → L2 HR Manager (any, `autoRecord`). SLA 48h business, breach=reminder/12h.
- **advance:** HR Manager only (manager skipped — emergency-sensitive). SLA 24h calendar, breach=escalate.
- **comp (amount-gated escalation):** Reporting manager → Skip-level (if amount>100k) → Department head (>500k) → Management (>2M) → HR Manager+Management all-mode (>5M). SLA 72h business.
- **expense:** Reporting manager → Finance. SLA 48h.
- **ood:** Reporting manager. SLA 24h calendar, breach=visual.
- **exit:** Reporting manager → Department head → HR Manager+Management (all). SLA 120h.
- **asset:** Reporting manager → Company Admin. SLA 48h, breach=visual.
- **profile:** no approval (self-serve). **declaration:** no approval (auto-accept, HR record only).
- **bank:** HR Manager only (security-sensitive). breach=escalate.
- **regularization:** Reporting manager (reads `REGULARIZATION_CONFIG.approval_workflow` for manager-only / manager+HR / HR-only).
- **ot:** Reporting manager (auto-routed when OT threshold exceeded & eligible).
- **attendance_day:** Reporting manager L1 → HR Manager (if `ATTENDANCE_APPROVAL_CONFIG.level_2.enabled`); only active when attendance approval ON; breach=auto_finalize.
- **comp_off:** Reporting manager confirms holiday/weekend work.
- **ml / pat:** HR Manager direct (manager informed only) — per Maternity Benefit Act. SLA 72h.
- **bereavement:** Reporting manager fast-track; auto-approve if no response in 6h. SLA 6h calendar, breach=escalate.
- **marriage:** Reporting manager → HR Manager; invitation-card document required.
- **wfh:** Reporting manager only; does not consume leave balance.

**Delegations:** delegate handles chosen request types during a date window; new tasks route to delegate's inbox tagged "On behalf of you"; pre-existing tasks stay with principal; accountability/audit records both delegate action and principal; **no nested delegation**; principal not locked out.

---

## Roles & Permissions

- **Two role planes:** Company plane (`currentRole='company'`, PERSONAS) vs Platform plane (`currentRole='super'`, SA_ROLES). Toggled by `toggleRole()`; nav visibility via `applyPersonaVisibility()` (`data-persona`) and `applySaRoleVisibility()` (`data-sa-role`).
- **personaHas(feature)** gates company features; super bypasses all. Feature map includes ops, finance, assets-*, reports, perf-*, pulse, employee-only.
- **CURRENT_USER multi-hat:** acts as Company Admin / HR Manager / Manager — Tasks filters by hat.
- **ROLE_CATALOG + ROLE_DESIGNATIONS** define approver roles and assignees with three scope levels (auto org-chart, designated pool flat/department/project, specific person). Custom roles creatable via Role editor; deletion blocked while referenced in workflows.

---

## Feature Inventory (this module)

**Platform plumbing**
- Dual role planes (Company personas / Platform SA-roles) with nav gating.
- 7 company personas, 9 platform roles, feature-gating map.
- 19 request types → 8 filter groups; per-type configurable workflow routing with conditional/amount-gated multi-level approvals, any/all modes, SLA (business/calendar), approaching %, breach actions, reminder intervals, multi-channel notifications.
- Role catalog (built-in + custom), scope levels (auto/designated/specific), designations by flat/department/project; role editor with icon picker, scoping, usage guard.
- Delegations (scheduled/active, type-scoped, non-nested, audit-preserving).
- Tenant SLA/business-hours config.

**Tasks / Inbox**
- 3 tabs (Awaiting me / By me / All), role + type filters, urgent SLA banner, consolidated cross-module approvals card, task cards with skip-level & on-behalf badges, task detail modal with approval-chain stepper + comment, bell dropdown, bidirectional approve/reject.

**Directory**
- Search + dept/location/status filters, stats row, paginated table, bulk import, export (all/view), import template, manage columns, per-row generate-letter (11 letter types), comp review, advance, mark inactive, initiate exit.

**Profile (Employee 360)**
- 8 tabs + sub-tabs (Time 5, Compliance 4), customizable field captions, quick-switch, auto-computed status with reasoning, full CTC/statutory/tax breakdown, salary advances, tax declaration, family/nominees, documents vault with expiry, attendance/leave deep-dives.

**ESS**
- 9 tabs, punch in/out, 8 self-service request forms, payslips, claims (OCR), assets, consolidated My Requests, profile-change requests, OKR/performance.

**Candidate Portal**
- Progressive-unlock single-identity portal (offer→BGV→preboard→Day-1 ESS handoff).

**Settings (owned panes)**
- Workflows & routing, Approvers & roles, Roles & permissions, Notifications; plus full SETTINGS_CATS tree (Workspace, Modules, TA, Performance & Growth, Exit & F&F, Assets & IT, Finance, Integrations, Personal).

---

## Gaps (Missing but Required by enterprise standards)

1. **No persisted audit-trail entity.** Comments/decisions reference "visible in audit trail" but there is no `AUDIT_LOG` data structure capturing actor, action, before/after, timestamp, IP. Required for SOC2, Indian labour-law 7-year retention (the prototype itself claims 7-year retention) and dispute defense.
2. **No notification/reminder engine entity.** `notificationChannels` and `reminderIntervalHrs` are declared but there is no NOTIFICATIONS queue, template store, delivery-status, or escalation-target resolution. Without it, SLA breach/escalation actions cannot actually fire.
3. **No employee unique data model.** Directory rows and Profile are hardcoded literals (arrays), not a normalized EMPLOYEE entity with PII, statutory IDs, addresses, bank, family, documents. EMPLOYEES_MASTER holds only 6 fields. A canonical employee schema is required for every downstream module.
4. **Validation rules are absent.** ESS forms only mark `req:true`; no format validation (PAN regex, Aadhaar checksum, IFSC, email, date ranges, leave-balance sufficiency, advance-amount vs salary cap, max_consecutive_days, blackout windows). Leave policy config defines these constraints but nothing enforces them at submit time.
5. **No optimistic-concurrency / in-flight workflow snapshot.** Role/scope edits warn "in-flight requests keep original routing" but there is no persisted per-request routing snapshot, so a real system would re-evaluate mutated WORKFLOW_ROUTING incorrectly.
6. **Delegation date-window enforcement is decorative.** Status (scheduled/active) is a static string; no scheduler evaluates start/end against "now", and "no nested delegation" / "tasks before delegation stay with principal" are described but not modeled.
7. **No RBAC permission matrix at field/action level.** Gating is coarse (persona→feature). Enterprise needs field-level visibility (e.g. disciplinary records "HR + manager chain only"), action-level permissions, and segregation-of-duties (e.g. approver ≠ requester) — none enforced.
8. **Skip-level / org-chart resolution is fragile.** Computed only from a single `managerId` hop; no handling of vacant managers, matrix/dotted-line reporting, or cycles, and `reporting_manager` auto-resolution has no fallback when the chain is broken.
9. **No SLA clock/business-calendar engine or holiday calendar link.** `slaPreview` is text-only; there is no actual elapsed-time computation honoring `TENANT_SLA_CONFIG` business hours, timezone, weekends, and public holidays — so `slaBreached` is a hardcoded boolean.
10. **No data-residency / consent / document-retention lifecycle.** Candidate portal collects BGV consent and KYC docs, ESS exposes masked bank/PAN, but there is no consent record entity, encryption/key metadata, retention-clock, or right-to-erasure handling — mandatory under India DPDP Act and for BGV vendor data sharing.

*(Additional notable gaps: no idempotency on the `unshift`-based request creation; ESS "with whom" approver is a free string not an FK; no pagination/server contract; no localization despite ₹/India-specific statutory logic; no error/empty/loading states for async; no e-sign integrity record beyond a status string.)*
