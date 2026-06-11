# Module: Performance, Growth, Pulse AI & Reporting

Reverse-engineered from `atvantiq-people-prototype_2.html`. Source line refs in parentheses. The IHRMS is single-tenant, persona-gated (`personaHas()`, line 1274), with one live performance cycle, AI tiles ("AI Coach", "AI Calibration Advisor", etc.) layered onto every subtab. Personas: `employee`, `manager`, `hr`, `reviewer`, `finance`, `it`, `super`.

Three top-level screens are owned here: **`performance`** (a subtabbed suite), **`pulse`** (attrition-risk AI), **`reports`** (analytics engine). The performance screen dispatches on `perfTab` (line 17411) across 7 tabs, each with its own subtab state variable.

---

## Persona Capability Map (line 1288–1296)
| Capability key | Personas allowed |
|---|---|
| `perf` (module access) | employee, manager, hr, reviewer, finance, super, it |
| `perf-team` (Team Goals subtab) | manager, hr, reviewer, super |
| `perf-calibration` (Calibration subtab) | hr, reviewer, super |
| `perf-talent` (Talent tab) | manager, hr, reviewer, super |
| `perf-templates` | hr, super |
| `perf-analytics` (Analytics tab) | manager, hr, reviewer, finance, super |
| `perf-increment-amounts` (₹ visibility) | hr, finance, reviewer, super |
| `perf-payroll-view` (push-to-payroll) | finance, super |
| `pulse` | it, hr, super |
| `reports` | it, hr, finance, super, manager |

`super` always returns true. Blocked tabs render a lock screen (`perfBlocked()`, line 17421).

---

## Screen-by-Screen Audit

### 1. Performance · Overview (`renderPerfOverview`, 17431)
- **Purpose:** Live snapshot of active cycle, AI Performance Coach, pending-work tiles.
- **Actors:** All perf personas (HR/manager primary).
- **Inputs:** `PERF_CYCLE`, `PERF_GOALS`, `PERF_REVIEWS`, `PERF_PROMO`, `PERF_PIPS`, `PERF_INCREMENTS`, `PERF_FEEDBACK`, `PERF_CHECKINS`.
- **Outputs / UI Elements:**
  - **Header** with `+ New cycle` (opens `perf-cycle-create`) and `Reviews →` buttons.
  - **Active-cycle gradient banner:** name, period, type, eligible count, current stage; mini-milestones Goal freeze / Self due / Mgr due / Publish with colour-coded dates.
  - **AI Performance Coach tile** (6 insight cards, each click-navigates a tab): vague-goal count, "6 managers show rating inflation", "4 high performers without promotion plan", "Engineering goals only 30% aligned to OKRs", "3 employees need urgent 1:1", active-PIP/checkpoint.
  - **KPI tiles (row 1):** Active cycle, Pending self reviews (`eligible−self_done`), Pending mgr reviews (`self_done−mgr_done`), Calibration pending (`mgr_done−calib_done`).
  - **KPI tiles (row 2):** Goals at risk, High performers (rating≥4), Promotion ready, Active PIP.
  - **KPI tiles (row 3):** Low performers (rating≤2), Attrition risk `7` (from Pulse), Increment budget impact (₹ gated by `perf-increment-amounts`, else 🔒).
  - **Recent feedback list** (top 4, type pill + sentiment pill) and **Check-ins due list** with inline Conduct buttons.
- **Business Rules:** counters derived from cycle deltas; ₹ figures hidden unless privileged.
- **Permissions:** module-level; ₹ tiles gated.

### 2. Performance · Goals (`renderPerfGoals`, 17518) — subtabs my / team / okrs / checkins
Header buttons: `+ Check-in` (`perf-checkin`), `+ Set goal` (`perf-goal-create`). Team subtab hidden unless `perf-team`. Drawer opens when `perfSelected` set.

- **My Goals (`renderPerfGoalsMy`, 17533):** AI Goal Assistant tile (on-track %, weightage check, `✨ Suggest goals from OKR` → `perfAiSuggestGoals`). KPI tiles: Active goals, Overall progress (weighted avg of current×weight), Weightage (flags ≠100%), AI quality avg. Table cols: **Goal (+target/"⚠ no target set") | Type | Weight | Progress (bar) | Linked | AI quality | Status**. Row → drawer.
- **Team Goals (`renderPerfGoalsTeam`, 17573):** AI Team alignment tile (unlinked-goal count, quality flags). Grouped by owner; per-owner card with weightage sum + at-risk count; table with inline **Approve** button per goal.
- **Company OKRs (`renderPerfGoalsOKRs`, 17599):** AI OKR alignment tile. Cascade Company→Department→Team. Each OKR card: level, linked-to parent, owner, progress %, confidence. Per key-result row: title, target/current, progress bar (green≥70/amber≥40/rose). Linked employee goals shown as clickable ghost pills.
- **Check-ins (`renderPerfGoalsCheckins`, 17625):** AI coaching tile (overdue count, high-risk count, "escalate to PIP"). Table cols: **Employee | Manager | Period | Due | Risk pill | Status (done date/pending) | View/Conduct**.
- **Goal Drawer (`renderPerfGoalDrawer`, 17649):** AI Goal Quality panel when `ai_quality<60` (lists missing target / no OKR link / vague verb + **suggested rewrite** + `✨ Use this rewrite` → `perfAcceptAiRewrite`). Field grid: Type, Category, Weight, Start, End, Target, Current, Confidence, Reviewer, Linked OKR. Evidence list. Actions: View employee profile, Give feedback, Edit goal.

### 3. Performance · Feedback (`renderPerfFeedback`, 17694) — subtabs received / given / recognition / 360
Header: `+ Request 360` (`perf-360-request`), `+ Give feedback` (`perf-feedback-give`).
- **Received/Given/Recognition (`renderPerfFeedbackList`, 17708):** AI Sentiment summary tile (positive/neutral/negative counts, recurring strengths & concerns). Recognition filters to Praise + Client appreciation. Each feedback card: type pill, from→to, linked-goal ghost pill, text, #tags, date · visibility, sentiment pill.
- **360 (`renderPerf360`, 17745):** Per-subject card: respondents, received/total, due, anonymous flag, status pill. AI Summary tile (when closed) with clustered **Strengths** (green) / **Improvement areas** (amber) pills + suggested calibration rating. In-progress shows "waiting on N responses", `Send reminder`, `Read full responses/report`.

### 4. Performance · Reviews (`renderPerfReviews`, 17830) — subtabs cycles / self / manager / calibration / outcomes
Calibration subtab hidden unless `perf-calibration`. Header: `+ New cycle`.
- **Review Cycles (`renderPerfReviewCycles`, 17845):** 10-stage progress rail (draft→…→closed). Stat tiles Eligible / Self done / Mgr done / Calibrated. Buttons: jump to Self/Manager/Calibration, **Advance stage →** (`perfAdvanceCycle`, 18006).
- **Self / Manager reviews (`renderPerfReviewsList`, 17876):** AI Self-Review / Manager Review Assistant tile (self: drafts from goals+feedback+project hours; manager: flags rating-comment mismatch, bias language, missing evidence). Table cols: **Employee (+id) | Cycle | Self rating / Self-Mgr rating (+ "mismatch" pill if |self−mgr|≥2) | Status | Done on | View/Write→**. Write opens `perf-self-review` / `perf-manager-review`.
- **Calibration (`renderPerfCalibration`, 17901):** AI Calibration Advisor tile (named inflation/inconsistency callouts). **Company-wide distribution** bar chart vs target % per rating. **Manager-wise distribution** table: per-manager rating counts O/EE/ME/BE/U + AI flag "inflation" (top-2 ratings >70%) + Inspect. Per-review row: self/mgr ratings, **Adjust rating…** select, **Send back** (`perfSendBack`), **Add note** (`perf-calibrate`), **Approve & lock** (`perfApproveCalib`).
- **Outcomes (`renderPerfOutcomes`, 17959):** AI Outcomes tile + `✨ Publish N now` (`perfPublishAll`). "Ready to publish" table (Employee | Final rating | Increment ₹ gated | Effective | Publish). "Published" table (released). **Approved increments awaiting Payroll** table (gated by `perf-payroll-view`): Current/Revised CTC, Inc %, Bonus, Variable, Effective + **→ Push to Payroll** (`perfPushToPayroll`).

### 5. Performance · Talent (`renderPerfTalent`, 18017) — subtabs ninebox / promo / successors / pip
Gated by `perf-talent`. Header: `+ Nominate for promotion`, `+ Start PIP`.
- **9-Box (`renderPerf9Box`, 18031):** AI Talent insights tile. 3×3 grid Performance × Potential; each cell shows box label + people count + avatar chips; click → toast/drill. Axes Low/Mod/High perf × Low/Mod/High potl.
- **Promotion Readiness (`renderPerfPromo`, 18062):** Table cols **Employee | Current grade | Proposed grade | Inc % (gated) | Bonus (gated) | Effective | Rating | 9-box | Status | Approve**. Approve (`perfApprovePromo`, 18147) → creates/sets an increment record (feeds payroll).
- **Successors (`renderPerfSuccessors`, 18088):** Key roles (CTO, VP Sales, VP Engineering) with incumbent + successor candidates pulled from 9-box Stars/High-impact cells + "ready in" horizon + **Build dev plan**.
- **PIP (`renderPerfPIP`, 18115):** AI PIP Assistant tile. Per-PIP card: dates, mgr, HR, status pill, **Reason** box, improvement goals with progress bars, **Checkpoints** (due/scheduled/done, Conduct button), outcome buttons **Extend / Mark improved / Recommend termination** (`perfPipOutcome`).

### 6. Performance · Development (`renderPerfDevelopment`, 18202) — subtabs plans / careers / mentors / recommendations
Header: `+ Dev plan` (`perf-dev-plan-create`).
- **Plans (`renderPerfDevPlans`, 18215):** AI Development Coach + `✨ Generate plan from review` (`perfAiGenDevPlan`). Table: **Employee | Plan | Type | Skills | Mentor | Progress | Due | Open**.
- **Career Paths (`renderPerfCareerPaths`, 18236):** Hardcoded tracks (IC Engineering, People Manager, Sales) with level ladders, current/next markers, and requirements to reach next level + Build dev plan.
- **Mentorship (`renderPerfMentorship`, 18245):** Pairs table **Mentor | Mentee | Cadence | Focus | Status**.
- **Recommendations (`renderPerfRecommendations`, 18250):** Card grid of course/cert/mentor suggestions per employee (source: LinkedIn Learning, Pluralsight, Force Mgmt, Coursera, Udemy, Internal) + Assign / Open.

### 7. Performance · Analytics (`renderPerfAnalytics`, 18264)
Gated by `perf-analytics`. AI Analytics tile (inflation, attrition, PIP success %). Charts: **Performance distribution** bar (vs target %), **Goal completion** by status. **Department analytics** table: Dept | HC | Avg rating | Promos | PIP | Attrition risk. KPI tiles: Total reviews, PIP success %, Promo ratio, Inc budget (gated). Export button.

### 8. Pulse (AI) (`SCREENS.pulse`, 15254)
- **Purpose:** Attrition-risk prediction, next 90 days.
- **Actors:** it, hr, super.
- **UI Elements:** Header "Pulse · attrition risk", "Model v3.2 · refreshed daily". AI model-context banner (trained on 3 yrs exits + 47 signals, 89% hindsight accuracy, "How model works →"). Risk tiles: **High risk 7 (≥70%) | Medium 23 (40–69%) | Stable 218 (<40%) | Accuracy 82% (12mo)**. **Deep-dive card** (Karan Mehta, 78% risk, next 60d): signals grid (no leave 4mo, missed 1:1s, comp 14% below band, ONAQT activity ↓40%), recommended actions: **Schedule 1:1, Trigger comp review, Send pulse survey, Snooze 14d**.
- **Note:** Pulse data is hardcoded in the render (no `PULSE_*` entity); referenced by Overview's "Attrition risk 7" tile.

### 9. Reports (`SCREENS.reports`, 4238) — landing / viewer / builder
- **Landing (`renderReportsLanding`, 4244):** Header with `⏰ Schedules · N`, `+ Custom report`. AI Reporting insights tile (4 cards). KPI tiles: Prebuilt reports, Custom reports (4), Scheduled, Run this month (312). Category grid (9 modules, icon + desc + count). Category filter pills + search box. Recently-used cards. Reports list table: **Report | Module | Description | open→**.
- **Viewer (`renderReportViewer`, 4358):** Breadcrumb + category pill. Actions: **⏰ Schedule, ↓ Excel, ↓ PDF, ✉ Share**. Filters: Period (today/this week/this month/last month/this quarter/FY), Department, Location. Data table built from `def.cols` + `reportSampleRows()` (wired to live module data: EMPLOYEES_MASTER, LEAVE_BALANCES, EXIT_CASES, TA_HEADCOUNT). Footer: "Reports respect your access — row-level filters apply."
- **Builder (`renderReportBuilder`, 4411):** AI Smart-suggest input. 3-step: **Source** (primary module + join), **Columns** (draggable field pills + add field), **Filters & grouping**. Live preview table. Output formats: Table, Bar chart, Line chart, Pivot, CSV, Excel, PDF, Email.

---

## Entities (Data Model)

### PERF_RATING_SCALE (17272) — 5-point scale w/ forced-distribution targets
`{ key:int(1–5), label, short, color, pct }` — 5 Outstanding (O, 15%), 4 Exceeds expectations (EE, 25%), 3 Meets expectations (ME, 50%), 2 Below expectations (BE, 8%), 1 Unsatisfactory (U, 2%).

### PERF_GOAL_TYPES (17281)
`['KRA','KPI','OKR','Project','Behaviour','Learning','Compliance']`

### PERF_GOAL_CATEGORIES (17282)
`['Delivery','Quality','Customer','Revenue','People','Innovation','Compliance','Learning']`

### PERF_CYCLE (17284) — single live cycle object
`{ id, name, period, type('Half-yearly'), eligible:int, goal_freeze:date, self_due:date, mgr_due:date, calib_due:date, publish:date, stage:enum, self_done:int, mgr_done:int, calib_done:int, published:int, increment_required:bool }`. `stage` ∈ the 10-stage machine below.

### PERF_GOALS[] (17286)
`{ id, title, type(PERF_GOAL_TYPES), cat(PERF_GOAL_CATEGORIES), owner:empId, owner_name, reviewer:empId, reviewer_name, weight:%, start:date, end:date, target:str, current:%(0–100), confidence('high'|'medium'|'low'), ai_quality:int(0–100), linked:str|null (OKR id · label), status('not_started'|'on_track'|'at_risk'|'behind'|'completed'), evidence:string[] }`

### PERF_OKRS[] (17299) — cascading
`{ id, level('Company'|'Department'), title, owner, progress:%, confidence, linked_to:okrId(opt), keyresults:[{ id, title, target, current, progress:% }] }`

### PERF_CHECKINS[] (17316)
`{ id, emp, emp_name, mgr, period, due:date, done:bool, date_done:date, progress_summary, blockers, support, risk('low'|'medium'|'high'), next_action, next_due:date }`

### PERF_FEEDBACK[] (17323)
`{ id, from, from_name, to, to_name, type(PERF_FB_TYPES), date, linked_goal:goalId|null, text, visibility('private'|'manager-visible'|'employee-visible'|'hr-visible'), sentiment('positive'|'neutral'|'negative'), tags:string[] }`

### PERF_FB_TYPES (17331)
`['Praise','Improvement','Peer feedback','Manager note','Client appreciation','Project feedback','Incident feedback']`

### PERF_360[] (17335)
`{ id, subject, subject_name, cycle, respondents:int, received:int, anonymous:bool, due:date, status('in_progress'|'closed'), ai_summary:str|null, strengths:string[], improvements:string[] }`

### PERF_REVIEWS[] (17341)
`{ id, emp, emp_name, cycle, self_status('draft'|'pending'|'submitted'), self_rating:1–5|null, self_done:date|null, mgr_status, mgr_rating:1–5|null, mgr, mgr_done:date|null, reviewer, reviewer_status('pending'|'submitted'), final_rating:1–5|null, calibrated:bool, published:bool }`

### PERF_9BOX{} (17349) — keyed by `'{potential}-{performance}'` (1–3 each)
`{ label, color, people:[{ id, init, color }] }`. Labels: 3-1 Enigma, 3-2 Growth employee, 3-3 Star, 2-1 Dilemma, 2-2 Core contributor, 2-3 High impact, 1-1 Action needed, 1-2 Effective, 1-3 Trusted professional.

### PERF_PROMO[] (17361)
`{ id, emp, emp_name, current_grade, proposed_grade, current_ctc, proposed_ctc, inc_pct:float, bonus, variable, effective:date, nominated_by, rating:1–5, box:9boxKey, status('pending_reviewer'|'pending_hr'|'approved'), rationale }`

### PERF_INCREMENTS[] (17367) — feeds Payroll
`{ id, emp, emp_name, cycle, rating, current_ctc, revised_ctc, inc_pct:float, bonus, variable, effective:date, status('pending_hr'|'pending_payroll'|'approved'|'pushed_to_payroll'), pushed_to_payroll:bool }`

### PERF_PIPS[] (17373)
`{ id, emp, emp_name, started:date, end:date, mgr, hr, reason, status(PIP_STATUS), goals:[{ g:str, progress:% }], checkpoints:[{ date, status('due'|'scheduled'|'done'), note }] }`

### PIP_STATUS (17384)
`['draft','active','checkpoint_due','improved','extended','closed','termination_recommended']`

### PERF_DEV_PLANS[] (17387)
`{ id, emp, emp_name, type('Career path'|'Skill gap'|'PIP-linked'|'Promotion readiness'), title, skills:string[], training:string[], mentor, due:date, progress:%, mgr_comments, hr_comments }`

### PERF_INTEGRATIONS[] (17393)
`{ key, name, category('Project'|'Code'|'CRM'|'Learning'), connected:bool, sync, last, maps:str }` — Jira, GitHub, GitLab, Azure DevOps, Salesforce, Zoho CRM, LinkedIn Learning, Coursera, Udemy. Maps external signals → KPI evidence / Dev plan.

### REPORT_CATEGORIES[] (4148) — 9 modules
`{ id, label, icon, color, desc }` — payroll, attendance, leave, ta (Talent Acquisition), performance, exit, assets, compliance, headcount.

### REPORT_DEFS[] (4160) — 35 prebuilt reports
`{ id, cat:categoryId, name, desc, cols:string[], sample?:str }`. `sample` key wires to live data extractor (`reportSampleRows`, 4327): pay-register, att-monthly, lv-balance, ta-source, ex-fnf, hc-org.

### REPORT_SCHEDULES[] (4219)
`{ id, report, freq, channel('email'|'download to drive'), recipients, last:date, status('active'|'paused') }`

### Form Schemas (TA_FORM_SCHEMAS, in `Object.assign` blocks)
`perf-goal-create`, `perf-checkin`, `perf-feedback-give`, `perf-360-request`, `perf-cycle-create` (17775); `perf-self-review`, `perf-manager-review`, `perf-calibrate`, `perf-promo-nominate`, `perf-pip-create` (18152); `perf-dev-plan-create` (18288); `report-schedule` (4483). Each `{ title, icon, sub, fields[], note, onSubmit/onEdit }`.

---

## Review Cycle State Machine (10 stages)
Stage enum (`perfAdvanceCycle`, 18006; rail in `renderPerfReviewCycles`, 17847):
`draft → goal_freeze → self_review → manager_review → reviewer_review → calibration → final_rating → increment → outcome_release → closed`

| Stage | Actor | What happens |
|---|---|---|
| draft | HR | Cycle created (`perf-cycle-create`); forms/scale/calibration rules from Settings. |
| goal_freeze | Employee + Manager | Goals set & approved; weightage should total 100%; AI quality scored. |
| self_review | Employee | `perf-self-review`: AI drafts from goals+feedback+project hours; sets `self_rating`, `self_status='submitted'`. |
| manager_review | Manager | `perf-manager-review`: AI flags rating-comment mismatch + bias; sets `mgr_rating`. Mismatch pill if \|self−mgr\|≥2. |
| reviewer_review | Reviewer/HOD | `reviewer_status` advances; routed up the chain. |
| calibration | HR/Reviewer | Company + manager-wise distribution vs target curve; inflation flag (top-2 >70%); adjust rating / send back / add note / **Approve & lock** sets `calibrated=true`, `final_rating`. |
| final_rating | HR | Final rating frozen. |
| increment | HR/Finance | Increment amounts attached (`PERF_INCREMENTS`); ₹ gated. |
| outcome_release | HR | Publish (`perfPublishOne`/`perfPublishAll`): `published=true`, employee sees outcome, linked increment → `approved`. |
| closed | — | Increments **pushed to payroll** (`perfPushToPayroll`) sets `status='pushed_to_payroll'`, effective 1 Jul; surfaces in Payroll dashboard (line 13144). |

**Calibration & 9-box:** Calibration compares manager distributions to forced-target curve (15/25/50/8/2). 9-box (Performance×Potential) feeds promotion nominations and successor pools (Stars/High-impact → successor candidates). **Increment → Payroll linkage** is the cross-module bridge (Payroll dashboard shows "₹ N approved increments from Performance & Growth" with Push-to-Payroll).

---

## Talent Processes

**Promotion readiness:** Nominate (`perf-promo-nominate`) → `pending_reviewer` → `pending_hr` → `approved`. Approval auto-creates/sets a `PERF_INCREMENTS` record (grade jump + CTC + bonus + variable, effective date). Tied to 9-box box id and final rating.

**Succession:** Key roles (CTO, VP Sales, VP Engineering) with incumbents; successors auto-matched from 9-box Stars (3-3) and High impact (2-3); "ready in" horizon; "Build dev plan" wires to dev-plan creation. AI flags thin benches.

**PIP lifecycle:** `draft → active → checkpoint_due → improved | extended | closed | termination_recommended`. Created via `perf-pip-create` (reason + ≤3 measurable goals + dates → auto 3-checkpoint schedule, HR auto-tagged). Checkpoints due→done (`perfPipCheckpoint`). Outcomes via `perfPipOutcome`. AI PIP Assistant flags risky wording. PIP-linked dev plans cross-reference (`type:'PIP-linked'`).

**Development & career paths:** Dev plans (Career path / Skill gap / PIP-linked / Promotion readiness) with skills, training, mentor, progress. Career ladders (IC/Manager/Sales tracks) show next-level requirements. AI generates plans from review comments.

**Mentorship:** Mentor-mentee pairs with cadence + focus; AI suggests pairings on skill overlap.

---

## Pulse AI
- **Surfaces:** Per-employee **attrition risk %** over next 60–90 days, bucketed High (≥70%) / Medium (40–69%) / Stable (<40%); model accuracy metrics.
- **Signals (47):** T&A patterns (no leave / burnout), engagement scores, comp ratios (below-band gap, months since revision), leave patterns, manager 1:1 cadence (missed/declined), ONAQT activity drop.
- **Data sources:** 3 years of exit data, attendance, comp/payroll bands, leave, calendar/1:1 cadence, project tool (ONAQT). Model v3.2, refreshed daily.
- **Actions:** Schedule 1:1, Trigger comp review, Send pulse survey, Snooze 14d. Explanations per prediction. Feeds Performance Overview "Attrition risk" tile and Analytics "attrition risk" column.

---

## Reporting Engine
- **9 categories** (REPORT_CATEGORIES) map 1:1 to modules: payroll, attendance, leave, TA, performance, exit, assets, compliance, headcount.
- **35 report definitions** (REPORT_DEFS) each with fixed `cols`. Performance reports: Rating distribution, Goals progress, PIP tracker. Others span payroll registers, statutory (PF/ESI/PT/24Q/gratuity), attrition/F&F, asset allocation/recovery, headcount/D&I/span.
- **Viewer:** filters Period / Department / Location; sample rows drawn from live module data; row-level access enforcement.
- **Export/formats:** Excel, PDF, CSV, Email/Share; builder adds Bar/Line chart, Pivot, Table.
- **Schedules** (REPORT_SCHEDULES): frequency (Daily / Weekly / Monthly Nth / Quarterly) + time + channel (email / Drive) + recipients; active/paused; runs as owner respecting access; failures retry + alert.
- **Custom builder:** Source + optional join, draggable columns, filters & grouping, AI smart-suggest from natural language, live preview.

---

## Feature Inventory (this module)

**Goals & OKRs:** goal CRUD with type/category/weight/target; AI goal-quality scoring (0–100) + auto-rewrite; weightage-100% check; OKR cascade Company→Dept→Team→Employee; goal↔OKR linkage; AI "suggest goals from OKR"; monthly/quarterly check-ins with risk + blockers + support + next-action; evidence attachments; integration-sourced KPI evidence (Jira/GitHub/Salesforce).

**Feedback & Recognition:** continuous tagged feedback with visibility levels; AI sentiment tagging; recognition feed; 360 reviews (manager/peer/reportee/client groups, anonymous, min respondents, reminder cadence, AI clustering of strengths/improvements + suggested rating).

**Reviews:** 10-stage cycle; AI-drafted self review; AI manager review (bias/mismatch detection); self-vs-mgr mismatch flag; calibration (company + manager distribution vs forced curve, inflation flag, adjust/send-back/lock); outcome release; increment input.

**Talent:** 9-box grid; promotion nomination & approval chain → increment creation; succession planning from 9-box; PIP lifecycle with checkpoints & outcomes; AI PIP assistant.

**Growth:** development plans (4 types) + AI generation; career-path ladders with requirements; mentorship pairing; AI learning recommendations from integrated platforms.

**Analytics:** rating distribution, goal completion, department analytics (avg rating/promo/PIP/attrition), PIP success rate, promo ratio, increment budget; export.

**Pulse AI:** attrition-risk scoring, explainable signals, recommended retention actions.

**Reporting:** 35 prebuilt reports across 9 modules, viewer with filters, custom builder, scheduled delivery, multi-format export.

**Cross-module:** Increment → Payroll push; probation reviews → performance cycles; 9-box → promotion/succession; Pulse → comp review trigger.

---

## Gaps (Missing but Required)

1. **No continuous-feedback/check-in cadence engine.** Check-ins and feedback are static records; there is no recurring scheduler, nudge/reminder automation, or auto-escalation to PIP after "2 missed cycles" (only mentioned in modal note text). Required for true continuous performance management.

2. **Goal cascade & alignment is cosmetic.** `linked` is a free-text string; there's no enforced parent-child OKR tree, no roll-up of child progress into parent KRs, and no alignment-coverage scoring beyond a hardcoded "30% aligned" AI line. Real OKR systems need bidirectional cascade with auto roll-up.

3. **Bell-curve / forced-ranking normalization not enforced.** Target % per rating exists (PERF_RATING_SCALE.pct) and inflation is *flagged*, but there is no automated normalization, ranking, or guardrail that prevents publishing an out-of-curve distribution. Calibration is advisory only.

4. **Comp-band / pay-equity linkage absent.** Increments carry CTC/inc% but there is no salary-band/range master, compa-ratio computation, budget-pool enforcement, or pay-equity check. Pulse references "14% below band" but no band entity backs it. Increment approval can exceed any budget unchecked.

5. **No analytics warehouse / historical trending.** All analytics derive from the single live cycle in memory; there is no multi-cycle history, year-over-year trending, cohort analysis, or persisted snapshot. Department averages are hardcoded constants, not computed.

6. **Reviewer/HOD and 9-box scoring lack a source.** `reviewer_status` advances but no reviewer review form/output exists. 9-box placement is a static map with no rule deriving potential/performance axes from ratings + assessments — placement cannot be recomputed.

7. **No competency/skills framework backbone.** Career paths reference "competency framework in Settings" and skills are free-text arrays; there is no skill taxonomy, proficiency levels, skill-gap computation, or assessment linkage. Recommendations are hardcoded.

8. **Weak audit/workflow & approval routing.** Approvals (promotion reviewer→HR→Finance, calibration lock, publish) mutate state with toasts; no audit trail, delegation, SLA, rejection-with-reason, or notification/email engine. PIP termination recommendation has no downstream exit-process handoff.

9. **PIP is single-record & not employee-linked to exit.** Only one PIP supported in fixtures; `termination_recommended` doesn't initiate offboarding/F&F. No legal-hold, acknowledgement capture, or document generation for PIP/letters.

10. **Pulse model & Reports are non-persisted / non-tenant-scoped.** Pulse is fully hardcoded (no entity, no per-employee scores, no model versioning store). Reports' "row-level access" and "runs as your tenant" are claims only — no RBAC enforcement, no scheduled-run execution log, no real export pipeline, and custom reports aren't persisted (Save just toasts).
