# Module: Time, Attendance, Leave & Timesheets

> Reverse-engineered from `atvantiq-people-prototype_2.html`. All field names, enums, statuses and labels are quoted verbatim from the source JS (data ~line 5748–7570; render funcs ~16442–25620). This is an in-memory prototype: all data is mutated in-place and re-rendered via `navigate()`. No persistence/back-end exists.

---

## Screen-by-Screen Audit

### 1. Time & Attendance Workspace (`ta` screen)
- **Purpose:** Daily/monthly reconciled attendance across all capture sources; hub for regularizations, OT approval, attendance day-approval, and HR override log.
- **Actors:** HR, Reporting Manager, Admin (viewers); employees only via ESS/profile.
- **Inputs:** `taDate` (date picker, default 2026-05-31), filters `taFilterDept` / `taFilterShift` / `taFilterLocation`, `taView`, `taMonthlyViewMode` (grid|list).
- **Outputs:** Reconciled per-employee day records via `reconcileAttendance(empId,date)`; stat tiles (present/late/halfDay/inProgress/absent/otHrs/pendingReg).
- **UI Elements:**
  - Page head: title "Time & Attendance"; sub-line "Daily attendance reconciled across N active sources · N employees · conflict policy: {policy}".
  - Buttons: date `input[type=date]`, "Export", "Sync sources" (primary, toast "Pulling latest events from biometric/face/ONAQT/mobile…").
  - Tabs (`pay-views`): `daily` "Daily attendance", `monthly` "Monthly calendar", `approval` "Pending approval · N" (only if `ATTENDANCE_APPROVAL_CONFIG.enabled`), `regularizations` "Regularizations · N", `ot` "OT approvals · N", `overrides` "Override log · N".
  - Inline filters (daily/monthly only): All depts / All shifts / All locations selects + clear (✕) button. Monthly adds Grid/List toggle.
- **Business Rules:** Conflict policy (`earliest`|`reliable`|`latest`) chooses firstIn/lastOut among duplicate punches; night-shift in-punches from prior calendar day are pulled into today's record; OT computed when `hours_worked > ot_threshold_daily_hrs` (9h).
- **Actions:** setTaView, setTaFilterField, navigate, openTaSourceMenu, sync (mock).
- **Permissions:** HR/Manager workspace; override + manual entry are HR-only.
- **Dependencies:** ATTENDANCE_EVENTS, SHIFTS, EMPLOYEE_SHIFTS, TA_CONFIG, ATTENDANCE_APPROVAL_CONFIG, REGULARIZATIONS, OT_PENDING, ATTENDANCE_OVERRIDES, HOLIDAYS, LOCATIONS.

### 2. Daily Attendance view (`renderTaDailyView`)
- Per-employee reconciled rows: first_in, last_out, hours_worked, status pill (`present`/`late`/`half_day`/`in_progress`/`absent`), ot_hrs, sources_used icons, location. Status pill colors: present=green, late=warn, in_progress=blue, else rose.

### 3. Monthly Calendar view (`renderTaMonthlyView`)
- Grid or List mode toggle; calendar cells per day with status; holiday-aware (HOLIDAYS) and weekend-aware (`workweek`, `half_day_on`).

### 4. Regularizations view (`renderTaRegularizationsView`)
- **Purpose:** Manager/HR review of employee claims for missing/incorrect punches.
- **UI:** 4 stat tiles (Pending / Approved this month / Rejected / Avg resolution "1.2d", target 2d). Pending cards: avatar, name, title·dept, type pill, "For {date} · submitted {submittedAt}", **Reason** block, claimed key/value pairs (`out_time`, `in_time`, `location`), actions **✓ Approve** / **Reject** / **View timeline**. "Recently resolved" table (Employee/Date/Type/Outcome/Resolved by).
- **Type labels:** `missing_in`→"Missing punch-in", `missing_out`→"Missing punch-out", `wrong_time`→"Wrong time recorded", `face_failed`→"Face match failed", `gps_failed`→"GPS failed".
- **Actions:** approveRegularization(id), rejectRegularization(id).

### 5. OT Approvals view (`renderTaOtView`)
- **Purpose:** Approve/reject auto-created overtime requests before payout.
- **UI:** Banner "How OT approval works" (threshold {ot_threshold_daily_hrs}h, {ot_default_rate_multiplier}× normal / {ot_holiday_rate_multiplier}× holiday) OR amber "Auto-approve mode is ON" banner when `!ot_requires_approval`. 5 stat tiles: Pending review (hrs), Approved this period, Rejected, Est. pending cost (₹, computed `ot_hrs*500*rate_mult`), Eligible employees (via `isOtEligible`). Status filter select (pending/approved/rejected/all) + "Approve all pending". Table cols: Employee, Date (+Holiday/weekday), Shift (color dot+name), Worked (first_in→last_out), OT hrs, Rate (`rate_mult`×), Reason, Status pill (+by approver), action ✓ Approve / Reject / View. Rejection-reason sub-row in rose.
- **Actions:** approveOt, rejectOt, bulkApproveOt, bulkApproveAllPendingOt.

### 6. Attendance Day-Approval view (`renderTaApprovalView`)
- **Purpose:** L1 (manager) → optional L2 (HR) sign-off on each day's captured attendance before payroll lock. Only active when `ATTENDANCE_APPROVAL_CONFIG.enabled` (OFF by default → shows "Attendance approval is OFF" empty state + "Configure in Settings →").
- **UI:** Banner naming L1/L2 roles, auto-finalize after N days. 4 tiles: Awaiting L1, Awaiting L2, Finalized today, Auto-finalize in {N}d. Three tables — Awaiting L1 (Employee/Date/Window/Hours/Sources icons/Flags[+OT,Holiday]/actions ✓ Approve + ✎ edit), Awaiting L2 (adds "L1 approved by", ✓ Finalize), Recently finalized.
- **Actions:** approveAttendanceDay(id,level), bulkApproveAttendanceL1, openAttendanceOverride.

### 7. Override Log view (`renderTaOverridesView`)
- Amber banner explaining HR can change any record (audit-traced; notify per config). Table: Employee, Date, Field pill, From→To (rose→green pills), Reason, Overridden by, When (+"✓ employee notified"). "Export log".

### 8. Attendance Override Modal (`renderAttendanceOverrideModal`)
- Opens via `openAttendanceOverride(empId,date,field,currentValue)`. Status field offers options: `present,late,half_day,wfh,leave,absent,holiday`. Mandatory reason (min 10 chars when `hr_override_requires_reason`). Save pushes to ATTENDANCE_OVERRIDES with `notified_employee` per `notify_employee_on_override`.

### 9. Source & Shift Menu (`renderTaSourceMenu` / `openTaSourceMenu`)
- Per-employee allowed punch sources + shift assignment management.

### 10. Leave & OOD screen (`leave` screen)
- **Purpose:** HR/Manager leave + OOD/WFH + comp-off management.
- **Page head:** "Leave & OOD"; sub "N pending · N on leave today · N active leave types". Buttons "📅 Team calendar", "⚙ Configure" (openSettingsPane('leave')), "+ Apply on behalf" (HR).
- **6-tile bento:** Pending approvals (leave+OOD), On leave today (% of team), OOD/WFH today (split), This month (approved), Comp-off pending.
- **Tabs (`leaveView`):** `pending` "Pending leave", `ood_wfh_pending` "OOD & WFH pending", `team_today` "Out today", `all_requests` "Leave requests", `ood_wfh_all` "OOD & WFH requests", `balances`, `calendar` "Team calendar", `comp_off` "Comp-off ledger".
- **Filters (pending/all_requests/balances):** All types / All depts / (all_requests:) All statuses + clear.
- Sub-views below.

### 11. Leave Pending view (`renderLeavePendingView`)
- Table: Employee, Type (pill code+icon; "no balance impact" note), Dates (start→end +half-day), Days (+"+N sandwich" warn), Reason (+"⚠ Balance short", "📎 doc attached"), Approval chain pills, Submitted (+"SLA breach" if submittedHrsAgo>48), actions ✓ Approve / Reject. "Approve all (N)".

### 12. Out Today view (`renderLeaveTeamTodayView`)
- Grouped by type (leave + OOD/WFH); cards with avatar, dept, 📍location, date range, day count. OOD/WFH tagged "— working, not in office".

### 13. All Leave Requests view (`renderLeaveAllRequestsView`)
- Full history table: Employee, Type, Dates, Days, Status pill (pending/approved/rejected/cancelled), Decided by, Submitted, chevron. "Export CSV".

### 14. Balances view (`renderLeaveBalancesView`)
- Matrix: rows=employees, cols=active balance-consuming leave types (code+short label) + Total avail. Cell: available (rose if <2) over used/accrued (+carryFwd in parens). "Export".

### 15. Team Calendar view (`renderLeaveCalendarView`)
- 14-day rolling grid; sticky employee col + day headers (weekend/holiday colored). Cells: H=holiday, —=weekend, leave code pill, OOD/WFH dashed-border pill, green dot=available. Prev/Next nav. Legend at bottom.

### 16. Comp-off Ledger view (`renderLeaveCompOffView`)
- AI tile "How comp-off works" (expires after `expiry_after_months`=3 mo). Table of COMP_OFF_LEDGER. "+ Claim on behalf" (HR) → openCompOffClaim.

### 17. OOD & WFH view (`renderOodWfhView(mode)`) — pending|all
- Lists OOD_REQUESTS with scope (`half_day`/`full_day`/`multi_day` tour + itinerary), location, purpose, travelMode/estimatedCost, approval chain. Approve/Reject via approveOodRequest/reject... .

### 18. Leave Detail Panel (`renderLeaveDetailPanel`) & OOD Detail Panel (`renderOodDetailPanel`)
- Slide-in detail for a selected request (leaveSelectedReq / oodSelectedReq) with full approval chain timeline.

### 19. Leave Apply Modal (`renderLeaveApplyModal`)
- **Fields:** (HR-on-behalf:) Employee picker*; Leave type tile-picker (active + show_in_ess; on-behalf shows all active) with per-type available balance; start/end dates; half-day; reason; doc attach (per type `requires_doc`). Live checks: balance shortfall (`balShort`), blackout overlap (`blackout_dates`), sandwich days. Routes via WORKFLOW_ROUTING.leave.
- **Actions:** openLeaveApply, updateLeaveDraft, closeLeaveApply, submit.

### 20. OOD Apply Modal (`renderOodApplyModal`) & Comp-off Claim Modal (`renderCompOffClaimModal`)
- OOD: type (ood/wfh), scope, date(s)/half slot, location*(ood), purpose*(ood), travelMode, estimatedCost. Comp-off: employee, earnedOn, hours, reason.

### 21. Timesheet screen (`timesheet` screen)
- **Purpose:** Client→Project→Task time logging, submit→PM→Manager approval, billing push.
- **Page head:** "Timesheet"; sub "{preset} preset · Client → Project → Task · {cadence} cadence · {expected_hours_per_week}h/wk target". "+ Create" menu (New project / client / task / time entry / rate card). Context submit button (Submit week·Nh / ● Submitted / ✓ Approved).
- **6-tile bento:** My week (Nh/40h, target met/short), My billable %, Pending approvals, Team submitted %, Active projects.
- **Tabs (`tsView`):** `my` My timesheet, `pending` "Pending approvals · N", `billing` (+push count), `team` Team week, `projects` "Projects · N", `utilization`. `my` tab has week nav (‹ ›).
- Sub-views: renderMyTimesheet (weekly grid/daily/timer per `default_entry_mode`), renderTsPendingView (bulk select+approve), renderTsBillingView (push to Zoho), renderTsTeamView, renderTsProjectsView, renderTsUtilizationView, renderCopyWeekModal.

### 22. My Timesheet / Entry (`renderMyTimesheet`, tsSubmitAddEntry)
- Weekly grid by project/task × day; entry fields: date, projectId, taskId, category, hours, notes, startTime/endTime. Week-lock (`tsIsWeekLocked`): before freeze_date, or approved (`freeze_after_approval`); admin unlock (audited). Copy-from-previous-week. Auto-fill from attendance/leave/OOD; attendance cap enforcement.

### 23. Timesheet Pending Approvals (`renderTsPendingView`, tsApprove/tsReject)
- Bulk select (`tsBulkSelected`), "Approve all". tsApprove(id,'pm'|'manager'): pm→`pm_approved`, manager→`approved`+auto-queue billable hours to Zoho Books push queue. Comment thread per timesheet (TS_COMMENTS). Audit (TS_AUDIT_LOG).

### 24. Profile › TIME_SUB.attendance tab (~16445)
- Self-view for one employee (mock ATV-0023). Monthly summary tiles: Days present (of workdays), Late arrivals (avg check-in), Half days (day loss), Hours worked (avg/day), OT hours (eligible?), WFH days. Today card (shift, first/last, hours, OT). Shift assignment card (color, start→end, break, rotation note) + Manage. Allowed punch sources (Restricted/All-sources pill, trust /5). Source usage 30-day bars. Pending items (Regularizations, OT) with Review→. Quick actions (Manage sources & shift / Add manual entry / View in T&A). Recent activity timeline (raw events: date·time, IN/OUT pill, source icon+label, location·device, trust pill).

### 25. Profile › TIME_SUB.leave tab (~16641)
- Per-type balance cards (available, used·accrued·carryFwd, year-end action via `yearEndAction`); pending/approved history; comp-off list.

### 26. ESS › Attendance tab (`renderEssAttendance` ~25418)
- "This month" stats (Present days, WFH days, Late marks, Avg hours). Quick log actions: ⏰ Regularize attendance, ➕ Submit overtime, 🏡 Request WFH/OOD, ◷ Fill timesheet. "Needs your attention · regularization" table (ESS_REGULARIZE: Date/Issue/Regularize→). Recent attendance table (Date/In/Out/Hours/Source/Status pill present|short|wfh).
- Forms open via `taOpenForm('ess-regularization'|'ess-ot'|'ess-wfh')`.

### 27. ESS › Leave tab (`renderEssLeave` ~25468)
- Leave balance bento (first 4 types). "WFH / OOD" + "+ Apply leave" buttons. "Leave & OOD history" table (Type/Details/Submitted/Approver/Status) from ESS_REQUESTS.

---

## Entities (Data Model)

### TA_CONFIG (~6090)
`conflict_policy('earliest'|'reliable'|'latest')`, `late_threshold_min:15`, `half_day_threshold_hrs:4`, `ot_enabled:true`, `ot_threshold_daily_hrs:9`, `ot_threshold_weekly_hrs:48`, `ot_default_rate_multiplier:2.0`, `ot_holiday_rate_multiplier:2.5`, `ot_requires_approval:true`, `geo_fence_enabled:true`, `geo_fence_radius_m:100`, `mobile_selfie_required:false`, `auto_punch_out_at:'23:59'`, `workweek:[mon..sat]`, `half_day_on:['sat']`. Plus `ot_eligibility:{applies_to_depts,applies_to_shifts,applies_to_employees,exempted_employees}` (~6371).

### TA_PENALTIES (~6109)
`late_grace_min:15`, `late_free_per_month:3`, `late_penalty_per_offense:0.5`, `late_reset_period('monthly'|'quarterly'|'never')`, `late_severe_threshold_min:60`, `late_severe_treatment('half_day'|'full_lop'|'absent')`, `short_hours_threshold_hrs:4`, `short_hours_treatment`, `missing_punchout_grace_days:2`, `missing_punchout_treatment`, `missing_punchout_default_hrs:8`, `absent_without_notice_treatment('lop'|'leave_balance'|'lop_then_leave')`, `continuous_absence_days_warn:3`, `continuous_absence_days_escalate:5`, `weekends_count_in_absence:false`, `early_departure_grace_min:15`, `early_departure_penalty('none'|'half_day'|'pro_rata')`, `escalation_enabled`, `escalation_tiers[{after_offenses,warning}]` (verbal_by_manager@5, written_by_hr@10, formal_letter_pip@15), `apply_to_probationers`, `apply_to_management`, `notify_employee_on_penalty`.

### ATTENDANCE_SOURCES (~6152)
`{key,label,icon,category('hardware'|'app'|'integration'|'manual'|'bulk'),trust(1-5),active,vendor,note}`. Keys: `bio, face, mobile, onaqt, onaqt_mobile, manual, csv(inactive), kronos(inactive)`. EMPLOYEE_SOURCE_ALLOWLIST overrides per emp; `getAllowedSources(empId)`.

### SHIFTS (~6164)
`{id,name,code,start,end,break_min,type('day'|'evening'|'night'),locations[],night_allowance,color}`. Values: general/GEN 09–18, general-flex/GENF, mumbai-10-7/MUM, morning/MOR 06–14, evening/EVE 14–22 (allowance 150), night/NIG 22–06 (allowance 300).

### SHIFT_ROTATIONS (~6174)
`{id,name,pattern[],period('weekly'|'monthly'),dept[],active}` — ops-24x7, security, engg-oncall(inactive).

### EMPLOYEE_SHIFTS (~6181)
`{empId:{shift_id,rotation_id,since}}`.

### Shift resolution (`resolveShiftForEmployee`)
employee assignment > LOCATION_DEFAULT_SHIFTS (mumbai→mumbai-10-7) > DEPT_DEFAULT_SHIFTS (engineering/sales/finance/people-ops→general; operations→null) > SHIFTS[0] General.

### HOLIDAYS (~6205)
`{date,name,type('regional'|'national'|'optional'),locations[]}`.

### ATTENDANCE_EVENTS (~6214)
`{id,empId,date,time,source,type('in'|'out'),trust,location,device?}`. Reconciled by `reconcileAttendance()` → record `{empId,date,shift_id,shift_name,shift_start,shift_end,first_in,last_out,hours_worked,status('present'|'late'|'half_day'|'in_progress'|'absent'),ot_hrs,sources_used[],event_count,events[],location}`.

### REGULARIZATIONS (~6318)
`{id,empId,date,type('missing_out'|'missing_in'|'wrong_time'|'face_failed'|'gps_failed'|'source_unavailable'),reason,claimed{out_time|in_time|location},status('pending'|'approved'|'rejected'),submittedAt,approvedBy?}`.

### REGULARIZATION_CONFIG (~6523)
`max_per_employee_per_month:5`, `window_days:30`, `allowed_types[]`, `custom_types[{key,label,description}]`, `auto_approve_same_day:false`, `auto_approve_threshold_min:30`, `approval_workflow('manager_only'|'manager_hr'|'hr_only')`, `send_reminder_to_manager_after_hrs:24`, `notify_employee_on_resolution:true`, `triggers{missing_punch_out,missing_punch_in,very_late_out,source_failed_consecutive,source_conflict}` (each with enabled + action e.g. `notify_employee`/`suggest_regularization`/`auto_create_draft`/`notify_hr`).

### LOCATIONS (~6326)
`{code,name,city,state,is_metro,active}` — bangalore-hq, mumbai, delhi, wfh. EMPLOYEE_LOCATIONS maps emp→code.

### OT_PENDING (~6391)
`{id,empId,date,shift_id,regular_hrs,ot_hrs,is_holiday,rate_mult,status('pending'|'approved'|'rejected'),reason,submittedAt,approvedBy?,rejectedBy?,rejectedReason?,first_in,last_out}`.

### ATTENDANCE_APPROVAL_CONFIG (~6441)
`enabled:false`, `level_1{enabled,role:'reporting_manager',sla_hrs:48}`, `level_2{enabled:false,role:'hr_manager',sla_hrs:24}`, `hr_can_override_always:true`, `hr_override_requires_reason:true`, `auto_finalize_after_days:7`, `notify_employee_on_override:true`.

### ATTENDANCE_DAY_APPROVALS (~6452)
`{id,empId,date,status('pending_l1'|'pending_l2'|'finalized'),first_in,last_out,hours,sources[],submittedAt,has_ot?,is_holiday?,l1_approvedBy?,l1_approvedAt?,l2_approvedBy?,l2_approvedAt?}`.

### ATTENDANCE_OVERRIDES (~6486)
`{id,empId,date,field,from_value,to_value,reason,overridden_by,overridden_at,notified_employee}`.

### LEAVE_CONFIG (~6569)
`leave_year('calendar'|'fiscal'|'anniversary')`, `fiscal_year_start_month:4`, `sandwich_rule_enabled:true`, `sandwich_rule_applies_to:['el','cl','sl']`, `encashment_basis('basic'|'basic_da'|'gross')`, `encashment_max_per_year:30`, `carry_forward_window_months:12`, `half_day_default_allowed:true`, `team_calendar_visible_to('team'|'department'|'all'|'nobody')`, `blackout_dates[{label,start,end,applies_to[]}]`, `notify_team_on_approval:true`, `auto_approve_if_no_action_days:0`.

### LEAVE_TYPES_CONFIG (~6588) — 10 types
Keys: `el`(Earned), `cl`(Casual), `sl`(Sick), `ml`(Maternity, female, inactive), `pat`(Paternity, male, inactive), `comp_off`(Compensatory Off), `bereavement`(inactive), `marriage`(inactive), `wfh`(deprecated marker), `ood`(deprecated marker), `lop`(Loss of Pay, not paid, affects_payroll, HR-marked).
Each: `{key,label,code,icon,color,description,consumes_balance,is_paid,accrual{method('monthly'|'annual_upfront'|'event_based'|'earned'|'unlimited'),annual_entitlement,monthly_rate,pro_rate_for_new_joiners,qualifying_period_days},carry_forward{enabled,max_days,expiry_after_months},encashment{enabled,on_separation,during_employment,max_per_year},application{min_advance_notice_days,max_consecutive_days,half_day_allowed,sandwich_applies,requires_medical_after_days,requires_doc,blackout_applies,(max_per_month/location_required)},eligibility{probationers,gender('all'|'female'|'male'),after_months},active,show_in_ess}`. `yearEndAction(t)` derives Carry/Encash/Lapses.

### LEAVE_BALANCES (~6704)
`{empId:{typeKey:{accrued,used,available,carryFwd}}}`.

### LEAVE_REQUESTS (~6774)
`{id,empId,type,start,end,days,reason,status('pending'|'approved'|'rejected'|'cancelled'),submittedAt,submittedHrsAgo?,sandwichAdded?,balanceAfter?,balanceWarning?,docAttached?,halfDay('first_half'|'second_half')?,location?,approvedBy/approvedAt/rejectedBy/rejectedAt/rejectionReason?,approvalChain[{step,by,at,done,decision?}]}`.

### COMP_OFF_LEDGER (~6829)
`{id,empId,earnedOn,reason,hours,credit,status('pending'|'approved'),approvedBy,expiresOn,used,balance}`.

### OOD_CONFIG (~6842)
`ood_enabled`, `wfh_enabled`, `ood_min_advance_notice_hrs:24`, `wfh_min_advance_notice_hrs:12`, `ood_max_tour_days:30`, `wfh_max_per_month:8`, `ood_requires_location`, `ood_requires_purpose`, `ood_creates_attendance`, `ood_attendance_status:'present_ood'`, `wfh_attendance_status:'present_wfh'`, `travel_reimbursement_eligible`, `half_day_slots{first_half,second_half}`.

### OOD_REQUESTS (~6858)
`{id,empId,type('ood'|'wfh'),scope('half_day'|'full_day'|'multi_day'),date?/start?/end?/days?,half?,location?,purpose,itinerary[{date,location,purpose}]?,status,submittedAt,submittedHrsAgo?,travelMode?,estimatedCost?,attendanceCreated?,approvedBy?,approvedAt?,approvalChain[]}`. Approved → auto-creates attendance entry.

### TS_CONFIG (~6917)
`enabled`, `hierarchy_levels(2|3)`, `default_entry_mode('weekly_grid'|'daily_detail'|'timer')`, `expected_hours_per_day:8`, `expected_hours_per_week:40`, `approval_cadence('daily'|'weekly'|'biweekly')`, `week_start_day:1`, `lock_period_days:7`, `approval_workflow('manager_only'|'pm_only'|'pm_then_manager')`, `industry_preset`, auto-fills (`auto_fill_from_attendance/leave/ood`, `enforce_attendance_cap`, `flag_under_logged`, `flag_over_logged`), reminders (remind_employees/managers_day/time), display (`show_billable_pct_to_employee`, `show_rate_to_employee`, `weekend_visible`), locks (`freeze_date:'2026-04-30'`, `freeze_grace_days:14`, `freeze_after_approval`, `freeze_admin_override`).

### TS_CATEGORIES (~6955)
`billable, non_billable, internal, leave(auto_filled,locked), holiday(auto_filled,locked), bench`. Each `{key,label,color,requires_project,description}`.

### TS_INDUSTRY_PRESETS (~6965)
`it_services, construction, agency, internal` — each sets hierarchy_levels, default_entry_mode, approval_cadence, enforce_attendance_cap, show_billable_pct_to_employee, common_tasks[].

### CLIENTS (~6973)
`{id,name,code,industry,status('active'|'on_hold'),billing_currency,primary_pm,since,notes,source,external_id,last_synced_at,sync_direction('pull_only'|'none')}`.

### TS_PROJECTS (~6982)
`{id,clientId,code,name,start,end,status('active'|'on_hold'),billing_model('time_material'|'fixed_fee'|'internal'),budget_hours,used_hours,manager,team[],rate_card_id,tags[],description,billable_default,costCenterId,source,external_id,last_synced_at,sync_direction}`.

### TS_TASKS (~7026)
`{id,projectId,name,billable,estimated_hours,used_hours,status('in_progress')}`.

### TS_RATE_CARDS (~7461)
`{id,name,currency,rates[{role('principal'|'senior'|'mid'|'junior'),rate}]}`.

### TIMESHEETS (~7468)
`{id,empId,week_start,week_end,status('draft'|'submitted'|'pm_approved'|'approved'|'rejected'),total_hours,total_billable,submitted_at,submitted_to?,approved_at?,approved_by?,rejection_reason?,entries[{date,projectId,taskId,category,hours,notes,startTime?,endTime?}],approval_chain[{step,by,at,done,decision?}]}`.

### TS_AUDIT_LOG (~7274) / TS_COMMENTS / TS_REMINDERS_PENDING (~7303-7315)
Audit `{id,at,actor,actor_name,action,target,target_label,details,before,after}` (actions: submit/approve/reject/comment/edit/delete/push_queued/push_completed/freeze/unfreeze/copy_week/bulk_approve/reminder_sent). Comments keyed by ts id `{id,by,at,body,resolved}`. Reminders `{empId,week_start,last_nudge,channels[]}`.

### CC_CONFIG / COST_CENTERS (~7074) / CC_APPROVAL_TIERS (~7102)
CC `{id,code,name,type('operational'|'profit'|'service'),parent_id,owner_id,department_id,legal_entity,geo,budget_year,budget_amount,budget_currency,budget_period('annual'),actual_spent,committed,status('active'|'frozen'),is_rollup?,notes}` — hierarchical (ccRollup/ccPath/ccChildren). Tiers: <₹50k→cc_owner, <₹5L→finance_head, <₹50L→cfo, else→ceo_and_cfo.

### SYNC_SOURCE_META (~7246)
`atvantiq_native, zoho_books, tally, quickbooks, onaqt, jira, asana, linear, salesforce, hubspot, zoho_crm` — `{label,icon,color,description}`; `isSynced()` = source≠atvantiq_native (read-only).

### WORKFLOW_ROUTING (~5748) — relevant keys
`leave`(manager→hr_manager autoRecord; sla 48h business_days, reminder@12h), `comp`(conditional tiers by amount), `ood`(manager only, sla 24h calendar, visual), `regularization`(manager; reads REGULARIZATION_CONFIG.approval_workflow), `ot`(manager; auto-routed on threshold), `attendance_day`(manager→hr_manager conditional on level_2.enabled; onBreach `auto_finalize`), `comp_off`(manager). Each `{steps[{roles,mode('any'|'all'),condition?,autoRecord?}],slaHrs,slaBasis,approachingPct,onBreach('reminder'|'escalate'|'visual'|'auto_finalize'),reminderIntervalHrs,notificationChannels}`.

---

## Attendance Capture Model
- **Sources** (ATTENDANCE_SOURCES, trust 1–5): biometric(5), face(5), mobile-app+GPS/selfie(3), ONAQT desktop(4), ONAQT mobile field(4), manual-by-HR(2,audited), CSV(disabled), Kronos(not connected). Per-company `active` flag + per-employee `EMPLOYEE_SOURCE_ALLOWLIST`.
- **Geofencing config exists** (`geo_fence_enabled`, `geo_fence_radius_m:100`, `mobile_selfie_required`) but no enforcement logic — events carry only a free-text `location` string.
- **Shifts/Rotations:** fixed assignment, rotation patterns, location/dept defaults, resolution precedence as above. Night shift spans day boundary (handled in reconcile + auto_punch_out_at 23:59).
- **Holidays:** multi-location (`locations:['all']` or specific); drive calendar coloring.
- **Day status computation** (`reconcileAttendance`): gather emp events for date (+ prior-day night in-punch) → sort → pick firstIn/lastOut per `conflict_policy` → hours = lastOut−firstIn → status: no event=`absent`; in but no out=`in_progress`; hours<`half_day_threshold_hrs`(4)=`half_day`; lateMin>`late_threshold_min`(15)=`late`; else `present`. OT = hours−`ot_threshold_daily_hrs`(9) when `ot_enabled`. Duplicate same-type punches deduped (earliest wins / by trust).
- **Penalties** (TA_PENALTIES): late free-quota+escalation tiers, short-hours, missing-punchout grace, continuous-absence warn/escalate — config only, no computed enforcement in render path.

## State Machines
- **Regularization:** (employee submits) `pending` → approveRegularization → `approved` / rejectRegularization → `rejected`. Optional same-day auto-approve (<30min) per config; manager_only / manager_hr / hr_only chain.
- **OT approval:** auto-created `pending` (on eligible + over threshold) → approveOt/bulkApproveOt → `approved` (+approvedBy/At, "pays in next cycle") / rejectOt → `rejected` (+rejectedReason). Auto-approve mode bypasses queue when `!ot_requires_approval`.
- **Attendance day-approval:** `pending_l1` → approveAttendanceDay(1) → `pending_l2` (if level_2.enabled) else `finalized`; `pending_l2` → approveAttendanceDay(2) → `finalized`. Auto-finalize after `auto_finalize_after_days`(7). HR override at any state.
- **Leave request:** `pending` → approveLeaveRequest → `approved` / rejectLeaveRequest → `rejected`; also `cancelled`. Chain: Submitted → Manager → HR (>5 days / direct for some types).
- **Comp-off:** work logged → `pending` claim → manager confirm → `approved` (credit added, `expiresOn`). Consumed via leave type `comp_off`.
- **OOD/WFH:** `pending` → approveOodRequest → `approved` (`attendanceCreated:true`, auto attendance entry `present_ood`/`present_wfh`). Multi-day tour >2 days adds HR step.
- **Timesheet:** `draft` → tsSubmitTimesheet → `submitted` → tsApprove('pm') → `pm_approved` → tsApprove('manager') → `approved` (+auto-queue billable to Zoho push) ; tsReject → `rejected`. Lock: before freeze_date or once approved; admin unlock audited.
- **Cost-center spend approval:** amount-banded tiers (cc_owner / finance_head / cfo / ceo_and_cfo).

## Workflows
- **Multi-tier approvals** via WORKFLOW_ROUTING (any/all modes, amount-conditional steps for comp/exit).
- **SLA/reminders:** per-flow `slaHrs`, `slaBasis(business_days|calendar)`, `approachingPct`, `onBreach`, `reminderIntervalHrs`. Leave SLA breach flagged at submittedHrsAgo>48. Timesheet reminders Fri 16:00 (employees) / Mon 10:00 (managers); tsSendReminder/tsSendRemindersAll.
- **Dynamic Tasks inbox** (`getDynamicTasks`): pending leave + OOD/WFH + comp-off merged into TASKS for approver inbox with SLA breach flags.
- **Sync from external sources:** clients/projects from Zoho Books/ONAQT (`pull_only`, read-only when synced); approved billable timesheet lines pushed to Zoho Books push queue. Attendance "Sync sources" pulls biometric/face/ONAQT/mobile (mocked).

## Feature Inventory
- **Capture:** multi-source punch (bio/face/mobile-GPS/ONAQT/manual), per-employee allowlist, trust scoring, conflict reconciliation, night-shift handling, auto-punch-out.
- **Shifts:** fixed + rotation patterns, location/dept default resolution, night allowances.
- **Daily/monthly attendance** with dept/shift/location filters, grid/list, holiday+weekend awareness.
- **Regularization:** 6 built-in types + tenant custom types, auto-detect triggers, manager/HR approval, monthly cap & 30-day window.
- **Overtime:** eligibility rules (dept/shift/specific/exempt), auto-request, multiplier (2×/2.5× holiday), bulk approve, est. cost.
- **Attendance approval workflow** (optional L1/L2) + **HR override log** with mandatory reason & employee notification.
- **Leave:** 10 configurable types, accrual methods, carry-forward/encashment, sandwich rule, blackout dates, half-day, balances matrix, team calendar, apply-on-behalf, SLA.
- **Comp-off** ledger with expiry.
- **OOD/WFH** as duty pre-approvals (not leave) with itinerary, travel cost, auto attendance creation.
- **Timesheets:** Client→Project→Task, weekly grid/daily/timer, categories incl. billable, industry presets, attendance cap, copy-week, audit log, comments, freeze/lock, bulk approve, billing push, rate cards, utilization.
- **Cost centers:** hierarchical budgets, rollups, amount-tier approvals.

## Gaps (Missing but Required)
1. **Payroll integration for LOP/OT/encashment.** LOP `affects_payroll`, OT "pays in next cycle", encashment basis (basic/basic_da/gross) and comp-off are all referenced but there is no payroll engine wiring — values are display-only. Needed so attendance/leave outcomes actually hit salary.
2. **Leave accrual engine.** Accrual methods (monthly/annual_upfront/event_based/earned/unlimited), monthly_rate, pro-rate-for-new-joiners, qualifying_period_days are configured but no scheduler computes/credits balances over time; LEAVE_BALANCES are static seeds.
3. **Biometric/face/ONAQT device integration.** Sources list vendors/device counts but "Sync sources" is a mock toast; no real ingestion, dedup at device level, or device health monitoring.
4. **Geofencing / GPS validation.** geo_fence_enabled, radius, mobile_selfie_required exist but events store free-text location only — no coordinate capture, radius check, or selfie verification.
5. **Penalty computation & LOP automation.** TA_PENALTIES (late quotas, escalation tiers verbal/written/PIP, continuous-absence warnings, short-hours/missing-punchout treatment) are pure config; nothing computes offenses, escalates, or converts to LOP/leave deduction.
6. **Sandwich-rule & blackout enforcement in submission.** Config flags exist and the apply modal previews `sandwichAdded`/blackouts, but no server-side day computation that includes interleaved weekends/holidays into `days` or hard-blocks blackout overlaps.
7. **Balance validation / negative-balance handling.** `balanceAfter:-7.5` with `balanceWarning` is shown but approval can still proceed; no enforced LOP fallback (`absent_without_notice_treatment`) or block.
8. **Auto-finalize & SLA reminder scheduler.** auto_finalize_after_days, auto_approve_if_no_action_days, reminderIntervalHrs, send_reminder_to_manager_after_hrs require a background job/cron that does not exist in a static prototype.
9. **Holiday/leave-year/anniversary engine.** leave_year('anniversary'), fiscal vs calendar, carry-forward expiry windows need date-machine logic to reset/expire balances; not implemented.
10. **Notifications & audit beyond timesheets.** notify_employee_on_* / notify_team_on_approval / notificationChannels are flags only; no email/push delivery, and only timesheets have a real audit log (attendance/leave/OOD lack equivalent immutable audit trails for compliance).
