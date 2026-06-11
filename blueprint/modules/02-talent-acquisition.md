# Module: Talent Acquisition, Onboarding & BGV

> Reverse-engineered from `atvantiq-people-prototype_2.html` (SCREENS object + TA_* data structures, lines ~1823–4760, 6090+).
> Scope: full recruiting lifecycle (workforce planning → requisition → ATS → interviews → offers → BGV → onboarding → probation → confirmation), the candidate-facing Candidate Portal, and the single-identity bridge into ESS.

**Important note on naming:** The brief referenced `TA_CONFIG` (~6090) and `TA_PENALTIES` (~6109) as TA SLA structures. These are actually **Time & Attendance** structures (conflict policy, late thresholds, OT, attendance penalty tiers) and belong to the Attendance module, NOT recruiting. TA pipeline SLAs are expressed inline on records via `sla_due`, `sla_days`, `expires`, `target_close`, and `age_days`. They are documented under Pipeline State Machine → SLAs with that clarification.

There is **no separate `ta` hub screen** in the SCREENS object. "Talent Acquisition" is a nav group; `ta-planning` is its landing screen (navigated to from the TA menu, see line 1516). The eight stage screens + `candidate-portal` are the real screens. A shared `taPageHead(stage, sub, actions)` renders the breadcrumb `◎ Talent Acquisition / <Stage>` for every stage screen.

---

## Screen-by-Screen Audit

### 1. `ta-planning` — Workforce Planning
- **Purpose:** Headcount & budget control per department for FY 2026-27; position management (positions persist even when vacant).
- **Actors:** HR/TA admin, BU heads, Finance (view).
- **Inputs:** `TA_HEADCOUNT`, `TA_POSITIONS`, `TA_BANDS`, `TA_GRADES`, `TA_REQUISITIONS` (joined by dept).
- **Outputs:** Headcount gap analysis, budget utilization %, fill progress, new positions, links to requisitions.
- **UI Elements:**
  - **AI banner** "Workforce intelligence" — computes total gap, % covered by open reqs, projected close date, budget utilization %.
  - **KPI strip (5 tiles):** Current headcount, Planned, Gap to fill, Budget (₹Cr + % utilized), Positions (+ open count).
  - **Table "Headcount plan by department":** columns Department (+ avg CTC ₹L), Current, Planned, Gap (pill: rose >20 / amber >5 / green), Fill progress (bar + %), Budget (used/total Cr), Open reqs (indigo pill). Row click → dept detail slide-over.
  - **Table "Position management":** columns Position, Grade / Band, Department, Headcount, Filled (x/y, green when full), Status (pill: filled=green, open=indigo, else amber), action "View req →". Row click → position detail.
  - **Dept detail modal (`renderTaDeptDetail`):** 4 tiles (Current, Planned, Fill %, Budget); list of positions in dept; list of open requisitions (click-through); footer "+ Add position", Close.
  - **Position detail modal (`renderTaPosDetail`):** 3 tiles (Headcount, Filled, Status); position-management explainer ("position reopens automatically when employee leaves"); linked requisition card or "Create requisition" CTA.
- **Buttons:** "Export plan", "+ New position" (opens `position` form).
- **Business Rules:** Positions persist when vacant; reopen automatically on attrition and can be re-requisitioned. Fill% color thresholds 90/70. Budget-gated requisitions optionally block reqs exceeding remaining dept budget (Settings → ta-org toggle).
- **Dependencies:** Grades/bands sourced from Settings → Org. Feeds requisitions.

### 2. `ta-requisitions` — Requisitions
- **Purpose:** Job requisitions, multi-step approval workflow, AI JD generation.
- **Actors:** Hiring Manager (raises), BU Head, Finance, HR (approvers).
- **Inputs:** `TA_REQUISITIONS`, `EMPLOYEES_MASTER` (hiring manager lookup), `TA_CANDIDATES` (pipeline).
- **Outputs:** Approved/pending requisitions, JD, pipeline summary.
- **UI Elements:**
  - **AI banner** "AI JD Generator" + button "✦ Generate a JD" (toast).
  - **KPI strip (4):** Open requisitions (+ openings left), Total openings (+ filled), Pending approval, Avg age (open).
  - **Filter tabs (`taReqFilter`):** All / Open / Pending approval (with counts).
  - **Table:** columns Requisition (title + ✦ AI badge + id/dept/location/grade/band), Hiring manager (avatar+name), Openings (filled/openings), Pipeline (applied/offer summary or "not sourcing yet"), Priority (pill: high=rose/medium=amber/low=mute), Approval (dot chain green/rose/line + n/total), Status (pill: open=indigo, pending_approval=amber).
  - **Detail modal (`renderTaReqDetail`):** key facts (Openings, Budget CTC, Range, Age); **Approval workflow** stepper (✓/number, step, by, at); AI-generated **Job description** with skill pills; **Pipeline summary** (applied/screening/interview/offer/joined counts); footer "View candidates →".
- **Buttons:** "Templates", "+ New requisition" (opens `requisition` form).
- **Business Rules:** Approval chain Hiring Manager → BU Head → Finance → HR. New reqs from form start `status:'pending_approval'`, `age_days:0`, empty pipeline. `jd_ai_generated` shows the ✦ spark.
- **Validation:** Form requires `title`; grade picked from `TA_GRADES`.

### 3. `ta-recruiting` — Recruiting (ATS)
- **Purpose:** Applicant tracking (kanban), candidate list, sourcing, internal mobility; the **candidate record is the spine** of the whole module.
- **Actors:** Recruiters, hiring managers, referrers.
- **Inputs:** `TA_CANDIDATES`, `TA_PIPELINE_STAGES`, `TA_REQUISITIONS`, interviews/assessments/offers/bgv (cross-linked).
- **View tabs (`taRecruitingView`):** Pipeline | All candidates (active count) | Sourcing | Internal mobility.
- **UI Elements:**
  - **Pipeline (kanban, `renderTaPipeline`):** AI candidate-scoring banner; requisition `<select>` filter (`taPipelineReq`); columns = active stages `applied, screening, interview, offer, bgv, preboard, onboarding` (each with color dot, label, ✦ if `ai`, count badge); cards show avatar, name (⭐ hero), exp·location, AI match score (color by ≥85/≥70), source pill. "Drag cards between stages" implied.
  - **All candidates (`renderTaCandidateList`):** table cols Candidate (avatar/exp/location), Role/Req, AI match, Stage (pill), Source (+ referrer name), Expected CTC, Notice (days). Excludes rejected/dropped.
  - **Sourcing (`renderTaSourcing`):** 3 tiles (Job boards=5, Referrals active, Talent pool=247); **Career portal preview** (careers.atvantiq.com, open roles, multi-language EN·HI·AR·FR·DE); **Employee referrals** table (Candidate, Referred by, Stage, Bonus ₹50K once offer+); **Talent pool tagged** list (Java 38, React 31, Finance 24, Leadership 12, Sales 45, Data Science 19).
  - **Internal mobility (`renderTaMobility`):** skill-marketplace AI banner; internal postings table (Role, Department, Type [Promotion/Transfer], Internal applicants, Status).
  - **Candidate record modal (`renderTaCandidateRecord`) — THE SPINE:** header avatar + name + role/req/exp/location; **Lifecycle stepper** (9 stages applied→confirmed, done=✓ filled, active=ring); **AI match breakdown** (skills/experience/location/culture bars); **Profile** (resume-parsed skill pills, work history, education); **Journey timeline** (`stage_history` with note/at/by); **Linked records** chips (interviews →, assessments, offer →, BGV →, onboarding →); footer Reject / "Advance to next stage →".
- **Buttons:** "Career portal ↗", "+ Add candidate" (`candidate` form), per-record Reject / Advance (`taAdvanceCandidate`).
- **Business Rules:** `taAdvanceCandidate` walks `flow=[applied,screening,interview,offer,bgv,preboard,onboarding,probation,confirmed]` one step. Reject moves candidate to talent pool (toast). Confirmed/rejected/dropped have no advance.

### 4. `ta-interviews` — Interviews
- **Purpose:** Calendar scheduling, structured scorecards, AI summaries, panels, AI-proctored assessments.
- **Actors:** Interviewers, panel members, recruiters; candidates (join link).
- **Inputs:** `TA_INTERVIEWS`, `TA_PANELS`, `TA_ASSESSMENTS`, `TA_CANDIDATES`.
- **View tabs (`taInterviewView`):** Calendar | List (upcoming count) | Panels (count) | Assessments (count).
- **UI Elements:**
  - **Calendar (`renderTaIntCalendar`):** week grid Mon–Sun, prev/next/Today nav (`taCalWeek`), interviews keyed by date, weekend shading, today highlight, slot click → detail, empty slot "+ slot" → schedule form, 📹 video marker; legend (Scheduled=indigo, Completed=green, Video).
  - **List (`renderTaIntSchedule`):** Upcoming table (Candidate, Round, Panel·Interviewer, When, Mode pill 📹/🏢, Join →); Completed table (Candidate, Round, Interviewer, Overall score, Recommendation pill, recording marker).
  - **Panels (`renderTaIntPanels`):** tiles per panel — name, rounds, member avatars, count this quarter; click → edit panel form; "+ New panel".
  - **Assessments (`renderTaIntAssessments`):** AI-proctored banner; table (Candidate, Assessment, Type pill [⌨ Coding/📹 AI Video/📝 Test], Score /max color-coded, Status).
  - **Interview detail (`renderTaIntDetail`):** scheduled → "Join interview room"; completed → recording player mockup, **Scorecard** bars (per criterion /10), interviewer feedback, **AI summary** tile; footer recommendation pill.
  - **Assessment detail (`renderTaAssessDetail`):** big score /max; coding → per-problem pass/partial/fail + code snippet + AI-proctoring "no suspicious activity" note; video → AI analysis bars (communication/confidence/keyword_match) + sentiment pill.
- **Buttons:** "Calendar sync ↗", "+ Schedule interview" (`interview` form).
- **Business Rules:** Video rounds auto-create a meeting link from connected provider (Zoom). Recommendations: strong_yes/yes (green), no (rose), else amber. AI proctoring flags tab-switching, copy-paste, multiple faces.

### 5. `ta-offers` — Offers
- **Purpose:** Offer builder, comp simulator, candidate acceptance portal, AI drop-risk.
- **Actors:** Recruiter, HRBP, Finance, BU Head (approvers); candidate (accept/negotiate/decline).
- **Inputs:** `TA_OFFERS`, `TA_CANDIDATES`.
- **UI Elements:**
  - **AI banner** "Offer drop-risk AI" (predicts drop probability).
  - **KPI strip (4):** Offers out (+ accepted), Acceptance rate %, Pending response, High drop-risk.
  - **Table:** Candidate (⭐ hero highlighted), Role·Grade, CTC ₹L, Status (pill accepted=green/negotiating=amber/declined=rose/released=indigo), Drop risk (pill + score%), DOJ, Approval (dot chain n/total), action "Portal →" (accepted only).
  - **Offer detail (`renderTaOfferDetail`):** **Compensation breakdown** (Fixed, Variable/bonus, Joining bonus, ESOP, Total CTC); **Drop-risk analysis** AI tile (score% + narrative by band); **Approval workflow** (Recruiter→HRBP→Finance→BU Head); **Candidate acceptance portal preview** (Accept/Negotiate/Decline or "Accepted on …"); footer "Open pre-boarding portal →" (accepted) or "Generate letter".
  - **Comp simulator modal (`renderTaCompSim`, `taCompSimOpen`):** CTC range slider (band 26–38L), Fixed (82%)/Variable (13%)/Joining (5%) split, approx monthly take-home, budget-band warning (>32L needs BU Head + Finance).
- **Buttons:** "Comp simulator", "+ Create offer" (`offer` form), "Generate letter" (PDF with annexures + NDA, toast).
- **Business Rules:** Offer acceptance auto-triggers BGV (see hero `stage_history`). Offers above grade band auto-route extra Finance+BU Head approval. Accepted → pre-boarding portal opens.

### 6. `ta-bgv` — Background Verification
- **Purpose:** BGV packages, vendor marketplace, component-level tracking, adjudication of exceptions, digital consent.
- **Actors:** Recruiter, HRBP, Compliance (adjudication); candidate (consent); external vendors.
- **Inputs:** `TA_BGV_CASES`, `TA_BGV_PACKAGES`, `TA_BGV_VENDORS`, `TA_BGV_CHECK_LABELS`, `TA_CANDIDATES`.
- **View tabs (`taBgvView`):** Active cases (count) | Packages (count) | Vendor marketplace.
- **UI Elements:**
  - **AI banner** "AI fraud detection" (cross-references docs, flags forgeries/mismatches).
  - **KPI strip (4):** In progress (avg TAT 5d), Completed, Needs adjudication, Vendors connected/total.
  - **Cases table (`renderTaBgvCases`):** Candidate (⭐ hero), Package·Vendor, Components (per-check colored squares: completed-clear=green/completed-fail=rose/review=amber/in_progress=blue/pending=line + n/total), Risk score (color by band), SLA (due date), Status (⚠ review or pill).
  - **Packages (`renderTaBgvPackages`):** tiles — name, target, ✓ check list, n checks.
  - **Vendors (`renderTaBgvVendors`):** multi-vendor routing banner; table (Vendor, Regions, Supported checks pills, Avg TAT days, Status connected/Connect button).
  - **Case detail (`renderTaBgvDetail`):** risk-score header + component-progress bar; **component-level verification** rows (label, vendor_ref, completed_at, score, status pill); **Exception/adjudication** block (if `review_required`) — severity·category pill, detail, adjudication workflow Recruiter→HRBP→Compliance, buttons "✓ Clear (conditional)", "Escalate to Compliance", "Reject"; **Digital consent record** (at, IP, device, version); footer "View candidate portal →", "Download report".
- **Buttons:** "Re-verification", "+ Initiate case" (`bgv-case` form).
- **Business Rules:** Checks routed per country/role/speed via vendor marketplace. Exceptions require adjudication; conditional clearance allows join; reject blocks joining. Consent captured with IP/device/version. Risk bands low/medium/high.

### 7. `ta-onboarding` — Onboarding (+ Probation + Confirmation)
- **Purpose:** Candidate→employee conversion, role-based task orchestration (SLA-tracked), IT provisioning, learning, 30-60-90 probation, confirmation.
- **Actors:** HR, IT, Admin, Manager, Employee (task owners); HRBP (conversion); buddy/mentor.
- **Inputs:** `TA_ONBOARDING`, `TA_ONBOARD_TEMPLATES`, `TA_PROBATION`, `TA_CANDIDATES` (preboard), `EMPLOYEES_MASTER`.
- **View tabs (`taOnboardView`):** Active (count) | Role templates (count) | Probation (count).
- **UI Elements:**
  - **AI banner** "Onboarding orchestration" (auto-creates employee/payroll/attendance profiles, fires role tasks).
  - **Asset provisioning cross-link card** (to Assets module) — per preboard joiner: kit pills (Laptop, Monitor, Access card, Email, VPN, GitHub), "Reserve laptop"/"Create access tasks".
  - **Probation cross-link card** → Performance & Growth.
  - **KPI strip (4):** Pre-boarding, Active onboarding, In probation, Templates.
  - **Active (`renderTaOnbActive`):** Pre-boarding table (Candidate, Role, DOJ, progress bar, Portal →); Active onboarding table (Employee+emp_id, Role, DOJ, Task progress %, Buddy, view →).
  - **Templates (`renderTaOnbTemplates`):** tiles per role — tasks_count, dept pills, Edit template.
  - **Probation (`renderTaProbation`):** 30-60-90 banner; per-record card (name·role, emp_id·DOJ·probation_end·manager, status pill) with 3 columns 30 Day Learning / 60 Day Execution / 90 Day Ownership (goals, manager_rating /5, review_date); actions "Complete 90-day review", "✓ Confirm employee", "Extend probation".
  - **Onboarding detail (`renderTaOnbDetail`):** conversion-confirmation banner (payroll/attendance/leave/shift/hierarchy auto-created); **Task orchestration by dept** (HR/IT/Admin/Manager/Employee, each task: status circle, task, owner, SLA pill); **IT access provisioning** chips (provisioned/provisioning/pending); **Learning journey** (mandatory courses, completion); note "⚠ Confirmation blocked until all mandatory learning complete"; **Buddy program**.
- **Buttons:** "Templates", "+ Convert candidate" (`convert` form), "Simulate Day 1" (in portal).
- **Business Rules:** Conversion auto-creates employee code, corporate email request, payroll/attendance/leave profiles, reporting hierarchy, fires role onboarding template. Confirmation blocked until mandatory learning done. Probation 30/60/90 reviews convert into Performance cycles.

### 8. `ta-analytics` — Analytics
- **Purpose:** Funnel, time-to-hire, source effectiveness, diversity, recruiter performance, predictive AI.
- **Inputs:** Aggregated `TA_REQUISITIONS.pipeline` (built funnel), static source/diversity/recruiter sample data.
- **UI Elements:**
  - **AI banner** "Predictive hiring intelligence" (bottleneck detection, source conversion comparison).
  - **KPI strip (5):** Time to hire 28d, Time to fill 41d, Cost per hire ₹1.2L, Offer accept 75%, Quality of hire 4.2/5.
  - **Hiring funnel** (Applied→Screened→Interviewed→Offered→Joined, bars + stage conversion %).
  - **Source effectiveness** table (Source, Candidates, Conv %, Quality bar) — LinkedIn/Naukri/Referral/Campus/Indeed.
  - **Diversity dashboard** (gender split bar 58/40/2, region tiles North/South/Tier-2/Differently-abled).
  - **Recruiter performance** table (Recruiter, Hires, Avg TTH, Accept %) — Anjali Mehta/Meera Pillai/Ravi Kumar.
- **Buttons:** "Export", "This quarter ▾".
- **Related:** Reports module defines `rpt-ta-pipeline`, `rpt-ta-source`, `rpt-ta-offers`, `rpt-ta-bgv`, `rpt-ta-aging` (cat `ta`).

### 9. `candidate-portal` — Candidate Portal (candidate-facing)
- **Purpose:** Separate candidate-facing surface, **same login as ESS**; opens at offer acceptance; collects BGV consent/docs; progressively unlocks Day-1 details once BGV clears; hands off to ESS on Day 1.
- **Actors:** Candidate (primary); recruiter (preview).
- **Inputs:** `TA_CANDIDATES` (portal stages offer*/bgv/preboard/onboarding/probation/confirmed; offer-stage only if offer accepted), `TA_OFFERS`, `TA_BGV_CASES`, `TA_JOINED`.
- **UI Elements:**
  - **Explainer banner** "One portal, progressive unlock".
  - **Candidate selector** pills (firstname + phase: pre-board/cleared/employee).
  - **Pre-boarding portal (`renderTaPreboardPortal`):**
    - Identity-continuity strip (login = one identity candidate→employee→alumni) + phase pill.
    - **BGV gate banner** (cleared=green "Day-1 unlocked" / not=amber "BGV in progress").
    - **Hero welcome** (days-to-DOJ countdown, "Simulate Day 1 →" button, CEO welcome video).
    - **Progress tiles (4):** Documents verified, E-signatures signed, BGV status+risk, Tasks complete.
    - **Meet your team** (hiring manager, onboarding buddy, future teammates).
    - **Your Day 1** card — **gated/locked until BGV clears** (location, report time, equipment, access card, dress code).
    - **Document collection** (Aadhaar, PAN, Passport, Bank proof, Degree certificate, Previous payslips; statuses verified/uploaded/pending; OCR auto-fill).
    - **E-sign documents** (Offer Letter, NDA, Employment Agreement, Code of Conduct, IT & Security Policy, POSH Policy; signed/pending; "Sign now").
    - **Pre-joining checklist** (profile, upload docs, sign policies, Day-1 logistics, pre-joining ISMS module).
  - **Handoff state (`renderPortalHandoff`):** identity strip flipped to ✓ Employee (emp id); Day-1 celebration hero "Go to your Self-service (ESS) →"; **What carried over** grid (profile, verified docs, signed policies, payroll profile, attendance & leave profile, reporting hierarchy); first-week preview.
- **Business Rules:** Portal access = offer accepted onwards. Day-1 logistics locked until BGV `completed`. `taSimulateDay1` sets `TA_JOINED[id]=true`, issues `employee_id`. `taGoToEss` navigates to ESS with `essNewJoiner` set — same identity, no re-login.

---

## Entities (Data Model)

### TA_HEADCOUNT (department headcount/budget plan)
`dept` (string), `current` (int), `planned` (int), `gap` (int), `budget_cr` (float ₹Cr), `used_cr` (float), `open_reqs` (int), `avg_ctc_l` (int ₹L).

### TA_POSITIONS (persistent positions)
`id` (pos-NNN), `title`, `grade` (L1–L7), `band` (IC/M/E), `dept`, `status` (enum: open | approved | filled), `headcount` (int), `filled` (int), `req_id` (FK→req | null).

### TA_BANDS
`id` (IC/M/E), `name`, `desc`. Enum bands: IC=Individual Contributor, M=Management, E=Executive.

### TA_GRADES
`id` (g-lN), `grade` (L1–L7), `band` (IC/M/E), `level` (Junior/Mid/Senior/Lead/Manager/Senior Manager/Director), `ctc_min` (₹L), `ctc_max` (₹L), `positions` (int).

### TA_REQUISITIONS
`id` (req-NNN), `title`, `position_id` (FK|null), `dept`, `bu`, `cost_center`, `location` (Bengaluru/Mumbai/Remote/Delhi/Pune), `hiring_manager` (FK→EMPLOYEES_MASTER ATV-id), `grade`, `band`, `employment_type` (full_time), `openings` (int), `filled` (int), `budget_ctc_l` (₹L), `ctc_range` ([min,max] ₹L), `bonus_pct` (int), `priority` (enum: high|medium|low), `status` (enum: open | pending_approval | [closed/filled implied]), `opened` (date), `target_close` (date), `age_days` (int), `jd_ai_generated` (bool), `skills` (string[]), `approval_chain` ([{step,by,at,done,decision}]), `pipeline` ({applied,screening,interview,offer,joined} ints).
- approval_chain.step enum: Hiring Manager, BU Head, Finance, HR. decision: approved (rose if rejected implied).

### TA_CANDIDATES (the spine)
`id` (cand-NNN/cand-hero), `name`, `email`, `phone`, `req_id` (FK), `role`, `source` (enum: LinkedIn|Naukri|Referral|Campus|Indeed|Agency), `referrer` (FK→employee|null), `stage` (see state machine), `current_ctc_l`, `expected_ctc_l`, `experience_y` (float), `location`, `notice_days` (int), `avatar_color`, `init`, `photo` (null), `ai_match` (0-100), `ai_match_breakdown` ({skills,experience,location,culture}), `skills` (string[]), `education` ([{degree,school,year,gpa}]), `work_history` ([{company,title,from,to,duration}]), `resume_url`, `stage_history` ([{stage,at,by,note}]), `offer_id` (FK|null), `bgv_case_id` (FK|null), `onboarding_id` (FK|null), `probation_id` (FK|null), `employee_id` (ATV-id|null), `assessment_score`, `interview_avg`, `offer_drop_risk` (low/medium/high|null), `reject_reason` (string, rejected only).

### TA_PIPELINE_STAGES
`key`, `label`, `color`, `ai` (bool, screening only). Keys: applied, screening, interview, offer, bgv, preboard, onboarding, probation, confirmed.

### TA_INTERVIEWS
`id`, `cand_id` (FK), `round` (L1 Technical/L2 System Design/Hiring Manager/Sales Round/HR Round/Culture Fit), `panel`, `interviewer`, `scheduled` (datetime), `duration_min`, `mode` (enum: video | in_person), `status` (enum: scheduled | completed), `recording` (file|null), `scorecard` ({criterion:score/10}|null), `overall` (float|null), `recommendation` (enum: strong_yes|yes|no|null), `feedback`, `ai_summary`.

### TA_PANELS
`name`, `members` (string[]), `rounds`, `count` (int).

### TA_ASSESSMENTS
`id`, `cand_id` (FK), `type` (enum: coding | video | test), `name`, `score` (int|null), `max`, `status` (enum: completed | in_progress), `breakdown` ({problemN: passed|partial|failed}), `time_taken_min`, `proctored` (bool), `ai_signals` ({communication,confidence,keyword_match,sentiment}).

### TA_OFFERS
`id`, `cand_id` (FK), `req_id` (FK), `role`, `grade`, `ctc_l` (₹L), `breakdown` ({fixed_l,variable_l,joining_bonus_l,esop_l}), `status` (enum: accepted | negotiating | released | declined), `released` (datetime), `responded` (datetime|null), `expires` (date), `doj` (date), `drop_risk` (low/medium/high), `drop_risk_score` (0-100%), `approval_chain` ([{step,by,done}]). Step enum: Recruiter, HRBP, Finance, BU Head.

### TA_BGV_PACKAGES
`id`, `name`, `target`, `checks` (check-key[]).

### TA_BGV_VENDORS
`id`, `name`, `regions` (string[]), `status` (enum: connected | available), `avg_tat_days` (int), `checks` (check-key[]). Vendors: AuthBridge, IDfy (connected), OnGrid, SpringVerify, First Advantage, HireRight.

### TA_BGV_CHECK_LABELS (check-key enum)
identity, education, employment, address, criminal, credit, reference, social_media, global_watchlist.

### TA_BGV_CASES
`id`, `cand_id` (FK), `package` (FK), `vendor` (FK), `status` (enum: in_progress | completed), `risk_score` (0-100), `risk_band` (low/medium/high), `initiated` (datetime), `sla_due` (date), `consent` ({accepted,at,ip,device,version}), `checks` ([{key,status,result,score,vendor_ref,completed_at,exception}]).
- check.status: completed | in_progress | review_required | pending. check.result: clear | discrepancy | null. exception: {severity (minor/major), detail, category (e.g. tenure_mismatch)}.

### TA_ONBOARD_TEMPLATES
`id`, `role`, `tasks_count` (int), `depts` (string[]). Roles: Software Engineer, Sales Employee, Finance Employee, Intern, Contractor, Senior Leadership.

### TA_ONBOARDING
`id`, `cand_id` (FK), `emp_id`, `name`, `role`, `template` (FK), `doj`, `buddy` (FK), `mentor` (FK), `manager` (FK), `progress_pct` (int), `tasks` ([{id,dept,task,owner,status,sla_days,due}]), `learning` ([{course,status,mandatory}]), `it_provisioning` ([{system,status}]).
- task.status: done | in_progress | pending. task.dept: HR/IT/Admin/Manager/Employee. learning.status: completed/in_progress/not_started. it_provisioning.status: provisioned/provisioning/pending.

### TA_PROBATION
`id`, `cand_id` (FK), `emp_id`, `name`, `role`, `doj`, `probation_end`, `manager` (FK), `status` (enum: in_progress | [completed/extended implied]), `plan` ({d30,d60,d90: {goals,status,manager_rating(/5),review_date}}).

### TA_JOINED
Map `{candId: true}` — flips candidate to "joined" once across Day 1 (single-identity carry into ESS). `essNewJoiner` holds the name for the ESS first-day welcome.

### TA_SETUP_STEPS
`key` (settings pane id), `label`, `done` (bool), `desc`. Steps: ta-org, ta-sourcing, ta-interviews-cfg, ta-offers-cfg, ta-bgv-cfg, ta-onboarding-cfg.

### TA_SOURCING_CHANNELS
`id`, `name`, `type` (Job board/Internal/Program/Vendor), `status` (connected/available), `icon`, `color`, `candidates` (int), `desc`. LinkedIn, Naukri, Indeed, Monster, Foundit, Employee Referral, Campus Hiring, Recruitment Agencies.

### TA_VIDEO_PROVIDERS / TA_CAL_PROVIDERS
Video: Zoom (connected), Google Meet, Microsoft Teams, Cisco Webex — `{id,name,status,icon,color,desc}`. Calendar: Google Calendar (connected), Outlook Calendar.

### TA_FORM_SCHEMAS (form-driven entity creation)
Form types: requisition, position, candidate, interview, offer, bgv-case, convert, department, grade (+edit/delete), band, agency, panel (+edit/delete), offer-template (+edit), bgv-package, onboard-template (+edit), channel-config, video-config, bgv-vendor. Each: `{title, editTitle?, icon, sub, fields:[{k,label,type,opts,req,ph,full}], note, onSubmit, onEdit?, onDelete?}`.

### NOT this module (clarification)
`TA_CONFIG` (line ~6090) and `TA_PENALTIES` (~6109) = **Attendance** config (conflict_policy, late_threshold_min, OT rates, geo-fence; late/short-hours/absence penalty tiers & escalation). Mislabeled in brief; documented in the Attendance module.

---

## Pipeline State Machine

**Stages (TA_CANDIDATES.stage):**
```
applied → screening → interview → offer → bgv → preboard → onboarding → probation → confirmed
                                                                  (terminal: rejected | dropped)
```
- `taAdvanceCandidate` / lifecycle stepper use the 9-stage flow above (probation+confirmed extend the active set). Kanban shows only active stages `applied…onboarding`. `rejected`/`dropped` are excluded from active lists; rejected candidates carry `reject_reason` and go to the talent pool.
- **Stage colors:** applied=mute, screening=blue(✦AI), interview=indigo, offer=amber, bgv=pink, preboard=blue, onboarding=indigo, probation=amber, confirmed=green.
- **Key auto-transitions:** offer **accepted** → BGV auto-triggered (hero `stage_history`: "Offer accepted → BGV auto-triggered" by system). BGV cleared → preboard Day-1 unlock. Day 1 (`taSimulateDay1`) → onboarding + employee identity issued. Probation 90-day confirm → confirmed.

**SLAs / time fields (no dedicated TA penalty object exists):**
- Requisition: `age_days`, `target_close`.
- Offer: `expires` (response deadline), `doj`.
- BGV case: `sla_due`; vendor `avg_tat_days` (4–8d); KPI "avg TAT 5 days".
- Onboarding tasks: per-task `sla_days` + `due`.
- (Attendance penalties in TA_PENALTIES are unrelated.)

**Candidate ↔ Employee identity bridge (single identity):**
- One login from application through employment. `TA_CANDIDATES.employee_id` links to `EMPLOYEES_MASTER`. `TA_JOINED[candId]` marks Day-1 crossing.
- Candidate Portal (offer-accept onward) and ESS share the same login. On Day 1 `taGoToEss` hands off; profile, verified docs, signed policies, payroll/attendance/leave profiles and reporting hierarchy carry over with **nothing re-entered**.

---

## Workflows

**1. Requisition approval**
Hiring Manager raises req (form / from position) → `status:pending_approval` → approval_chain Hiring Manager → BU Head → Finance → HR. Each step records by/at/decision. All approved → `status:open` → sourcing begins. Reqs over grade band route extra Finance + BU Head.

**2. Offer approval & e-sign**
Recruiter builds offer (comp simulator validates vs grade band) → approval_chain Recruiter → HRBP → Finance → BU Head → `status:released` → candidate acceptance portal (Accept/Negotiate/Decline by `expires`). Accept → `status:accepted`, `responded` set, BGV auto-triggers, pre-boarding portal opens. E-sign of Offer/NDA/Employment Agreement/Code of Conduct/IT & Security/POSH happens in the candidate portal (timestamped).

**3. BGV vendor flow**
Initiate case (package + vendor) → candidate gets secure consent link → digital consent captured (IP/device/version) → checks auto-trigger via vendor API → component-level results stream in (clear/discrepancy/score/vendor_ref) → exceptions go to adjudication (Recruiter → HRBP → Compliance): Clear (conditional) / Escalate / Reject. Cleared → Day-1 logistics unlock in portal.

**4. Onboarding task templates**
Candidate converted (`convert` form) → auto-creates employee code, corporate email request, payroll/attendance/leave profiles, reporting hierarchy → fires role-based template (`TA_ONBOARD_TEMPLATES`) → SLA-tracked tasks across HR/IT/Admin/Manager/Employee + IT provisioning + mandatory learning + buddy program. Confirmation blocked until all mandatory learning complete.

**5. Probation confirmation**
30-60-90 plan (Learning/Execution/Ownership) with manager ratings /5 per checkpoint → "Complete 90-day review" → "✓ Confirm employee" (confirmation letter, permanent) OR "Extend probation". Reviews feed Performance cycles.

---

## Integrations implied
- **Sourcing/job boards:** LinkedIn, Naukri, Indeed, Monster, Foundit, Employee Referral portal, Campus drives, Recruitment Agencies portal (per-channel auto-post / auto-import / spend cap).
- **Career portal:** careers.atvantiq.com, company-branded, multi-language (EN·HI·AR·FR·DE).
- **Video interview:** Zoom (connected), Google Meet, Microsoft Teams, Cisco Webex (auto meeting link + cloud recording + waiting room).
- **Calendar:** Google Calendar (connected), Outlook (invites to candidate + panel).
- **Assessments:** AI-proctored coding platform, AI video screening.
- **BGV vendors:** AuthBridge, IDfy (connected); OnGrid, SpringVerify, First Advantage, HireRight (India/GCC/US/Global) — API-driven, country/role routing.
- **E-sign:** offer letter, NDA, employment agreement, policies (timestamped digital signature).
- **AI services:** JD generation, candidate match scoring, interview AI summaries, assessment scoring/proctoring, offer drop-risk, BGV fraud detection, predictive hiring/bottleneck analytics, OCR document parsing.
- **Cross-module:** Assets (kit provisioning), Performance (probation→cycles), Payroll/Attendance/Leave (auto-profile creation), ESS (Day-1 handoff), Reports.

---

## Feature Inventory (this module)

**Workforce planning:** dept headcount/budget plan, gap analysis, budget utilization, persistent positions, position reopen-on-attrition, bands/grades source-of-truth, budget-gated reqs toggle.
**Requisitions:** AI JD generator, 4-step approval chain, priority, pipeline summary, age tracking, templates.
**ATS/Recruiting:** kanban pipeline (drag-advance), AI match scoring + breakdown, candidate spine record (lifecycle stepper, journey timeline, linked records), candidate list, sourcing (career portal, referrals + bonus, talent pool tags, agencies), internal mobility/skill marketplace.
**Interviews:** week calendar, scheduling, panels, structured scorecards, AI interview summaries, recordings, AI-proctored coding & AI video assessments.
**Offers:** offer builder, comp breakdown, comp simulator, 4-step approval, AI drop-risk, candidate acceptance portal, offer letter generation.
**BGV:** packages by tier, multi-vendor marketplace + routing, component-level tracking, risk scoring, exception adjudication workflow, digital consent, AI fraud detection, report download.
**Onboarding:** candidate→employee conversion, role-based SLA task orchestration, IT provisioning, mandatory learning (blocks confirmation), buddy/mentor, asset provisioning cross-link.
**Probation:** 30-60-90 plans, manager ratings, confirm/extend, feeds Performance.
**Candidate portal:** progressive unlock, BGV gate, doc collection (OCR), e-sign, pre-joining checklist, countdown, CEO video, single-identity ESS handoff.
**Analytics:** funnel, TTH/TTF, cost-per-hire, accept %, quality of hire, source effectiveness, diversity, recruiter performance, predictive AI; TA reports in Reports hub.
**Settings:** setup checklist + 6 config panes (org/grades, sourcing, interviews/video, offers, BGV, onboarding). 18 form schemas for create/edit/delete.

---

## Gaps (Missing but Required)

1. **No requisition rejection/return path in UI** — approval chain models `decision:'approved'` and renders rose for rejected, but there's no reject/send-back action or rejection reason capture. Real approval workflows must allow denial with comments and re-routing. *Why:* finance/BU heads will reject over-budget or unjustified reqs.

2. **No persistent server state / audit trail** — all mutations are in-memory array ops with toasts; no created_by/timestamps on most actions, no immutable audit log. *Why:* hiring decisions, BGV adjudication, and offer approvals are legally sensitive and must be auditable.

3. **Offer negotiation loop is cosmetic** — `status:negotiating` exists but no counter-offer capture, revised-CTC versioning, or re-approval trigger. *Why:* negotiation is core to offer management and affects budget approvals.

4. **No explicit recruiter/RBAC permission model** — screens assume a single TA-admin actor; no separation between recruiter, hiring manager, interviewer (scorecard-only), candidate (portal-only), compliance (adjudication-only). *Why:* interviewers must not see comp; candidates only see their own portal; compliance gates BGV.

5. **BGV consent & data-privacy compliance incomplete** — consent record exists but no DPDP/GDPR retention policy, data-deletion, candidate right-to-access, or vendor data-processing agreements. *Why:* BGV handles sensitive PII across jurisdictions (India/GCC/US).

6. **Onboarding tasks not linked to real owners/notifications** — task `owner` is a free-text name, no assignment to actual user accounts, no reminders/escalation when SLA breaches. *Why:* SLA-tracked orchestration is meaningless without escalation on breach.

7. **No duplicate-candidate / re-application detection** — adding a candidate never checks email/phone against existing candidates or the talent pool. *Why:* prevents duplicate pipelines and surfaces prior history/blacklist.

8. **No interview availability / panel scheduling intelligence** — scheduling is manual date entry; no interviewer availability lookup, conflict detection, or load balancing (analytics even flags "panel availability is the constraint" but no tooling addresses it). *Why:* the system's own bottleneck analysis demands it.

9. **Probation/confirmation gating not enforced end-to-end** — "Confirm employee" is a toast; no hard block tying confirmation to completed 90-day review + mandatory learning + BGV clearance. *Why:* confirmation is a legal status change requiring prerequisite verification.

10. **No offer/requisition budget reconciliation back to TA_HEADCOUNT** — creating reqs/offers doesn't decrement `used_cr`/`budget_cr` or update `filled` on positions; counts are static. *Why:* workforce planning loses its single-source-of-truth value if downstream hiring doesn't write back to the plan.

*Honorable mentions:* no candidate communication/email log, no scorecard aggregation/decision committee view, no offer-letter template variable binding, no multi-currency for GCC/US roles, no diversity data source (hardcoded), no re-verification scheduling despite the button.
