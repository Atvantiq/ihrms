# 18 — Database Design

Logical schema derived from the prototype's ~200 data structures, normalized and completed with the missing entities from `12-gap-analysis.md`. Organised by bounded context (each context owns its schema; cross-context references are by ID + events, not FKs across contexts).

## 18.0 Conventions

- **Every tenant-scoped table** carries `tenant_id UUID NOT NULL` with a Postgres **RLS policy** (`USING (tenant_id = current_setting('app.tenant_id')::uuid)`).
- PKs are `UUID` (v7 for time-ordering on high-volume tables).
- Audit columns on every table: `created_at, created_by, updated_at, updated_by, version (optimistic lock)`.
- **Effective-dated** entities use `(effective_from, effective_to)` ranges (job, comp, org placement).
- Money is `NUMERIC(15,2)`; rates `NUMERIC(9,4)`; never float.
- Soft-delete via `deleted_at` where retention requires; hard-delete only via governed deletion (DPDP).
- High-volume tables (`attendance_event`, `audit_event`, `notification`, `payroll_line`) are **partitioned** by `(tenant_id, month)` or range.

---

## 18.1 Platform / Control Plane (separate database)

```
tenant(id, name, slug, status[trial|active|attention|suspended|archived], region[in|eu|us],
       plan_id, mrr, employee_count, residency, deployment_stamp, created_at, activated_at)
plan(id, name, tier, pepm_price, currency, billing_cycle)
module(id, key, name)                          -- 15 modules
plan_entitlement(plan_id, module_id, included, limits_json)
tenant_entitlement(tenant_id, module_id, enabled, overrides_json)   -- per-tenant gating
metering_record(id, tenant_id, metric[active_employees|api_calls|ai_tokens|storage], value, period)
invoice(id, tenant_id, period, status[draft|issued|paid|overdue|disputed|refunded], subtotal, gst, total, currency)
invoice_line(invoice_id, description, qty, unit_price, amount)
payment(id, invoice_id, method, amount, status, gateway_ref, paid_at)
feature_flag(id, key, name, state[off|on|beta], rollout_pct, prerequisites_json, kill_switch)
feature_flag_target(flag_id, tenant_id, value)
release(id, version, ring[internal|alpha|beta|early|stable|enterprise_locked|custom], notes, status)
compliance_pack(id, name, jurisdiction, version, status[draft|legal_review|sandbox_preview|impact_analysis|approved|published|acknowledged|archived], effective_date)
compliance_pack_ack(pack_id, tenant_id, acknowledged_by, acknowledged_at)
statutory_rate(id, jurisdiction, type[epf|esi|pt|tds|gratuity|lwf], params_json, effective_from, effective_to, pack_id)
statutory_rate_history(...)                    -- append-only change log
announcement(id, title, body, status, scheduled_at, published_at, audience)
template(id, category, name, body, version)    -- global templates
tenant_template_install(template_id, tenant_id, installed_at)
integration_provider(id, name, category, config_schema_json)
tenant_integration(id, tenant_id, provider_id, status[healthy|paused|error], direction, config_json, last_sync)
sa_user(id, email, role[owner|ops|release|compliance|billing|security|ai|support|auditor])
impersonation(id, sa_user_id, tenant_id, status[pending_approval|active|completed|denied], approved_by, masking_on, started_at, ended_at, reason)
ai_policy(id, tenant_id, provider, model, budget_tokens, redaction_on, kill_switch)
ai_usage(id, tenant_id, model, tokens_in, tokens_out, cost, at)
sa_ticket(id, tenant_id, subject, status, priority, sla_due, rca_id)
webhook_subscription(id, tenant_id, url, events_text[], secret)
webhook_delivery(id, subscription_id, event, payload_json, status, attempts, delivered_at)
api_key(id, tenant_id, hashed_key, scopes_text[], last_used)
backup_policy / restore_job / dr_test / legal_hold / retention_policy / data_export_request   -- data governance
sa_audit_event(id, actor, action, target, at, immutable)   -- append-only
```

---

## 18.2 Identity, RBAC & Workflow (shared platform, tenant DB)

```
app_user(id, tenant_id, person_id?, email, status, sso_subject, mfa_enabled, last_login)
session(id, user_id, tenant_id, issued_at, expires_at, ip, device)
role(id, tenant_id, key, name, icon, scope_default)        -- ROLE_CATALOG
capability(id, key, module)                                  -- fine-grained permissions
role_capability(role_id, capability_id, scope[self|team|dept|location|establishment|tenant])
user_role(user_id, role_id, scope_ref)                      -- scope_ref = dept/location id
designation(id, tenant_id, name, role_mapping)              -- ROLE_DESIGNATIONS
delegation(id, tenant_id, principal_id, delegate_id, request_types_text[], from_date, to_date, active)

-- Workflow / approval engine
workflow_def(id, tenant_id, request_type, version, steps_json, sla_hrs, sla_basis[business|calendar],
             approaching_pct, on_breach[reminder|escalate|visual|auto_finalize], reminder_intervals_json, channels_text[])
request_type(id, key, group, label, config_json)            -- 19 types / 8 groups
workflow_instance(id, tenant_id, request_type, subject_ref, requester_id, status[submitted|in_progress|approved|rejected|returned|cancelled],
                  routing_snapshot_json, current_step, amount, sla_due, sla_state[ok|approaching|breached], created_at)
workflow_task(id, instance_id, step_no, assignee_id, mode[any|all], status[pending|approved|rejected|delegated], acted_by, acted_at, comment)

-- Notifications
notification_template(id, tenant_id?, key, channel, subject, body)
notification(id, tenant_id, user_id, channel[inapp|email|sms|push|whatsapp], template_key, payload_json, status[queued|sent|read|failed], sent_at)
notification_pref(user_id, category, channel, enabled, digest)

-- Audit (append-only, partitioned, hash-chained)
audit_event(id, tenant_id, actor_id, action, entity_type, entity_id, before_json, after_json, at, prev_hash, hash)

-- Documents
document_template(id, tenant_id?, category, name, body, version)
document(id, tenant_id, owner_type, owner_id, type, template_id, storage_key, status, generated_at)
signature_request(id, document_id, signer_id, provider, status[sent|signed|declined], signed_at)
consent_record(id, tenant_id, person_id, purpose, granted, granted_at, expires_at, evidence_key)  -- DPDP
```

---

## 18.3 Core HR

```
person(id, tenant_id, first_name, last_name, dob, gender, personal_email, phone,
       pan, aadhaar_enc, passport, marital_status, blood_group, emergency_contact_json)   -- one identity candidate→employee
employee(id, tenant_id, person_id, emp_code, status[probation|active|on_notice|exited|suspended],
         doj, confirmation_date, exit_date, work_email, employment_type)
employee_job(id, employee_id, effective_from, effective_to, department_id, designation_id, band_id, grade_id,
             location_id, reporting_manager_id, skip_level_id, cost_center_id, shift_id)   -- effective-dated
employee_comp(id, employee_id, effective_from, effective_to, ctc, structure_id, currency)  -- effective-dated
department(id, tenant_id, name, head_id, parent_id)
designation(id, tenant_id, name); band(id, tenant_id, name); grade(id, tenant_id, name)
location(id, tenant_id, name, address, geo_lat, geo_lng, geofence_radius, holiday_calendar_id, timezone)
establishment(id, tenant_id, name, pf_code, esi_code, pt_code, tan, pan, address)          -- statutory registration
bank_account(id, person_id, account_no_enc, ifsc, bank_name, primary)
nominee / education / prior_employment / family_member / employee_document   -- profile sub-entities
employee_skill / disciplinary_record / award                                 -- compliance/perf profile tabs
helpdesk_case(id, tenant_id, employee_id, category, subject, status, sla_due, workflow_instance_id)
```

---

## 18.4 Talent Acquisition

```
headcount_plan(id, tenant_id, dept_id, year, budgeted, filled, open)
position(id, tenant_id, title, band_id, grade_id, dept_id, location_id, status)
requisition(id, tenant_id, position_id, hiring_manager_id, status[draft|pending|open|on_hold|filled|cancelled],
            openings, priority, workflow_instance_id, sla_due, target_close)
candidate(id, tenant_id, person_id?, employee_id?, name, email, phone, source, current_stage
          [applied|screening|interview|offer|bgv|preboard|onboarding|probation|confirmed|rejected|dropped],
          req_id, owner_id, age_days)
application(candidate_id, req_id, stage, applied_at)
pipeline_stage(id, key, order)
interview(id, candidate_id, round, type, panel_id, scheduled_at, video_link, status, scorecard_json)
panel(id, tenant_id, name, member_ids_text[])
assessment(id, candidate_id, type, score, result)
offer(id, candidate_id, req_id, ctc, components_json, status[draft|pending|released|accepted|declined|expired],
      version, workflow_instance_id, esign_doc_id, expires)
bgv_case(id, candidate_id, package_id, vendor_id, consent_id, status[initiated|running|results|adjudication|clear|discrepancy|fail], checks_json)
bgv_package(id, checks_text[]); bgv_vendor(id, name, api_config_json)
onboard_template(id, tenant_id, name, tasks_json)
onboarding(id, candidate_id, template_id, status, tasks_json[owner,sla,done])
probation(id, employee_id, plan[30_60_90], checkpoints_json, status[active|confirmed|extended|terminated])
sourcing_channel(id, tenant_id, name, type[jobboard|referral|campus|agency|portal], config_json)
```

**Bridge rule:** on Day-1, `candidate.employee_id` is set; `person` is shared; `employee` row created from candidate data. No re-entry.

---

## 18.5 Time, Attendance, Leave, Timesheet

```
attendance_source(id, tenant_id, type[biometric|gps|face|web|mobile|manual], config_json)
employee_source_allow(employee_id, source_id)
shift(id, tenant_id, name, start, end, break_min, grace_min, ot_after)
shift_rotation(id, tenant_id, pattern_json); employee_shift(employee_id, shift_id, effective_from)
holiday(id, tenant_id, calendar_id, date, name, optional)
attendance_event(id, tenant_id, employee_id, ts, type[in|out], source_id, geo_json, selfie_key, device_id)   -- partitioned
attendance_day(id, tenant_id, employee_id, date, status[present|late|half_day|wfh|leave|absent|holiday|weekend],
               in_ts, out_ts, hours, ot_hours, lop, source_used, approval_state[pending_l1|pending_l2|finalized])
regularization(id, employee_id, date, type[missing_in|missing_out|wrong_time|face_failed|gps_failed], reason, workflow_instance_id, status)
ot_record(id, employee_id, date, hours, status[pending|approved|rejected], approver_id)
attendance_override(id, employee_id, date, by, reason, before_json, after_json, at)

leave_type(id, tenant_id, name, code, paid, accrual_rule_json, max_balance, carry_forward, encashable, half_day_allowed, deprecated)
leave_balance(id, employee_id, leave_type_id, year, opening, accrued, used, encashed, balance)
leave_accrual_txn(id, employee_id, leave_type_id, date, amount, reason)   -- accrual engine ledger
leave_request(id, employee_id, leave_type_id, from_date, to_date, days, half_day, reason,
              status[pending|approved|rejected|cancelled], workflow_instance_id)
comp_off_ledger(id, employee_id, earned_date, expiry_date, status[available|claimed|expired], claim_request_id)
ood_request(id, employee_id, type[ood|wfh], from_date, to_date, reason, status, workflow_instance_id)  -- auto-creates attendance_day

client(id, tenant_id, name, industry)
project(id, tenant_id, client_id, name, billing_model[time_material|fixed_fee|retainer|internal], status)
project_task(id, project_id, name, billable)
timesheet(id, employee_id, week_start, status[draft|submitted|pm_approved|approved|locked])
timesheet_entry(id, timesheet_id, date, project_id, task_id, category[billable|non_billable], hours, start, end, notes)
rate_card(id, project_id, role, rate, currency)
cost_center(id, tenant_id, name, type[operational|project|service|profit], budget, actual, committed)
cc_approval_tier(cost_center_id, threshold, approver_role)
ts_audit_log(id, timesheet_id, actor, action, at); ts_comment(id, timesheet_id, by, body, resolved)
```

---

## 18.6 Payroll, Statutory, Tax

```
salary_component(id, tenant_id, name, code, type[earning|deduction|reimbursement|employer],
                 calc[fixed|pct_basic|pct_ctc|pct_gross|balancing|slab|computed|formula], formula, tax[taxable|partial|exempt], sequence)
salary_structure(id, tenant_id, name, components_json)
pay_group(id, tenant_id, name, establishment_id, pay_cycle)
payroll_run(id, tenant_id, pay_group_id, month, stage[draft|preview|approved|bankfile|paid], totals_json, held_json, approved_by, paid_at)
payroll_line(id, run_id, employee_id, gross, net, earnings_json, deductions_json, employer_json, tds, lop_days, held, hold_reason)   -- partitioned
tds_computation(id, employee_id, fy, regime[old|new], projected_income, deductions_json, tax, rebate, surcharge, cess, monthly_tds)
tax_declaration(id, employee_id, fy, regime, declarations_json, status[open|submitted|proof_pending|verified|locked], verified_by)
tax_proof(id, declaration_id, type, amount, document_id, verified)
advance(id, employee_id, purpose, amount, status[requested|active|paid_off|rejected|cancelled], schedule_json, outstanding)
company_account(id, tenant_id, bank, account_no_enc, ifsc, purpose)
bank_file(id, run_id, format, storage_key, generated_at); bank_txn(id, run_id, employee_id, amount, utr, status)
statutory_filing(id, tenant_id, establishment_id, type[ecr|esic|pt|24q|form16], period, status, artifact_key, challan_ref)
gl_journal(id, tenant_id, run_id, entries_json, posted_at, external_ref)
```

---

## 18.7 Assets & Finance

```
asset(id, tenant_id, tag, category, status[available|reserved|allocated|in_transit|under_repair|returned|lost|damaged|disposed|written_off],
      assigned_to, purchase_date, cost, depreciation_method, book_value)
asset_request(id, tenant_id, requester_id, category, stage[draft|manager_review|it_approval|finance_approval|procurement|fulfilled|acknowledged], workflow_instance_id)
asset_license(id, tenant_id, name, seats, used, expiry, cost)
access_profile(id, tenant_id, name, systems_text[]); access_grant(employee_id, system, granted_at, revoked_at)
asset_audit(id, tenant_id, date, scope, findings_json)
asset_repair(id, asset_id, status[reported|under_review|sent_to_vendor|repaired|replaced|closed], vendor, cost)
asset_incident(id, asset_id, type, recovery_amount, exit_recovery_id)
depreciation_schedule(id, asset_id, period, opening, depreciation, closing)
purchase_order(id, tenant_id, asset_request_id, vendor, amount, status)
recovery(id, tenant_id, employee_id, type[notice|asset|loan|advance|bond|excess_salary], amount, source_ref, exit_case_id)
```

---

## 18.8 Performance & Growth

```
perf_cycle(id, tenant_id, name, period, type, stage[draft|goal_freeze|self_review|manager_review|reviewer_review|calibration|final_rating|increment|outcome_release|closed], dates_json)
perf_goal(id, employee_id, cycle_id, type[KRA|KPI|OKR|Project|Behaviour|Learning|Compliance], category, title, target, weight, linked_goal_id, status, progress)
perf_okr(id, cycle_id, objective, key_results_json, owner)
perf_checkin(id, employee_id, cycle_id, date, notes)
perf_feedback(id, from_id, to_id, type, body, at)
perf_360(id, cycle_id, subject_id, reviewer_id, responses_json)
perf_review(id, employee_id, cycle_id, self_rating, mgr_rating, reviewer_rating, final_rating, mgr_id, status)
perf_9box(id, employee_id, cycle_id, performance, potential, box)
perf_promo(id, employee_id, cycle_id, from_band, to_band, readiness, status)
perf_increment(id, employee_id, cycle_id, pct, amount, new_ctc, status, pushed_to_payroll)
perf_pip(id, employee_id, status[draft|active|checkpoint_due|improved|extended|closed|termination_recommended], checkpoints_json, exit_case_id)
perf_dev_plan / career_path / mentorship / succession_candidate / competency / competency_rating
```

---

## 18.9 Exit & F&F

```
exit_case(id, tenant_id, employee_id, type[voluntary|involuntary], reason, regrettable,
          stage[draft|submitted|manager_review|retention_review|accepted|notice_period|lwd_confirmed|exited],
          notice_date, lwd, workflow_instance_id)
kt_record(id, exit_case_id, status[not_started|in_progress|submitted|manager_review|approved], items_json)
clearance(id, exit_case_id, department[assets|it|finance|hr], status[pending|in_progress|cleared|dues_pending], dues_amount)
fnf(id, exit_case_id, flow[draft|hr_verified|finance_verified|payroll_approved|payment_processed|paid|closed],
    earnings_json, recoveries_json, statutory_json, net, eligibility_json)
exit_document(id, exit_case_id, type[relieving|experience|service|no_dues|fnf_statement|gratuity], document_id)
```

---

## 18.10 Reporting / Analytics (warehouse, CQRS read models)

```
report_def(id, tenant_id?, category, name, columns_json, source, filters_json)   -- 35 prebuilt + custom
report_schedule(id, report_def_id, cron, recipients_text[], format[xlsx|pdf|csv], status[active|paused])
report_run(id, report_def_id, params_json, status, artifact_key, ran_at)
-- plus denormalized fact/dim tables fed by CDC: fact_attendance, fact_payroll, fact_headcount,
-- fact_pipeline, fact_utilization, dim_employee, dim_org, dim_date, fact_attrition (Pulse)
```

## 18.11 Indexing & partitioning highlights

- Partition `attendance_event`, `audit_event`, `payroll_line`, `notification` by `(tenant_id, month)`.
- Composite indexes on `(tenant_id, status)` for all queue/inbox tables (`workflow_task`, `*_request`).
- GIN indexes on JSONB (`routing_snapshot`, `components_json`, `declarations_json`) where queried.
- Covering index on `workflow_task(assignee_id, status)` — powers the unified task inbox.
- BRIN on time-series partitions.

## 18.12 Referential integrity policy

- FKs **within** a context. **Across** contexts: store the foreign ID, validate via service/event, never a physical cross-schema FK (keeps contexts independently deployable/extractable).
