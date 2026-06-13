const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type EmploymentStatus =
  | "Active"
  | "Probation"
  | "Joining"
  | "Notice"
  | "Inactive";

export interface EmployeeListItem {
  employee_id: number;
  employee_code: string;
  full_name: string;
  email: string;
  designation: string | null;
  department: string | null;
  branch: string | null;
  manager_name: string | null;
  date_of_joining: string | null;
  tenure: string;
  status: EmploymentStatus;
}

export interface EmployeeDetail extends EmployeeListItem {
  first_name: string;
  middle_name: string | null;
  last_name: string | null;
  short_name: string | null;
  phone: string | null;
  date_of_birth: string | null;
  gender: string | null;
  division: string | null;
  circle_id: number | null;
  reporting_manager_id: number | null;
  date_of_leaving: string | null;
  fathers_name: string | null;
  mothers_name: string | null;
  marital_status: string | null;
  spouse_name: string | null;
  alternate_phone: string | null;
  pan_no: string | null;
  aadhaar_no: string | null;
  pii_visible: boolean;
}

export interface DirectoryStats {
  total: number;
  active: number;
  probation: number;
  joining: number;
  notice: number;
  inactive: number;
  departments: string[];
}

export interface EmployeeListOut {
  items: EmployeeListItem[];
  total_matches: number;
  stats: DirectoryStats;
}

async function authHeader(): Promise<Record<string, string>> {
  const { supabase } = await import("@/lib/supabase");
  const { data } = await supabase().auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Turn an error response into a human-readable message. Handles the API's
 *  envelope where `detail` is either a string (HTTPException) or a list of
 *  Pydantic field errors (422). For field errors we surface "field: message". */
async function errorMessage(res: Response): Promise<string> {
  const raw = await res.text();
  let detail: unknown = raw;
  try {
    detail = JSON.parse(raw).detail ?? raw;
  } catch {}
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const e = detail[0] as { loc?: unknown[]; msg?: string };
    const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : undefined;
    const msg = (e.msg ?? "Invalid value").replace(/^Value error,\s*/, "");
    return field && field !== "body" ? `${field}: ${msg}` : msg;
  }
  return `Request failed (${res.status})`;
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json", ...(await authHeader()) },
    cache: "no-store",
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
    throw new Error("Not signed in");
  }
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json() as Promise<T>;
}

export interface MeOut {
  employee_id: number;
  email: string;
  roles: string[];
  persona: string;
  is_hr: boolean;
}

export interface DirectoryMeta {
  departments: string[];
  divisions: string[];
  branches: string[];
  designations: string[];
  circle_ids: number[];
}

export interface EmployeeCreate {
  first_name: string;
  middle_name: string | null;
  last_name: string | null;
  email: string;
  phone: string;
  employee_code: string;
  gender: string | null;
  date_of_birth: string | null;
  designation: string;
  department: string;
  division: string;
  branch: string;
  circle_id: number;
  reporting_manager_id: number | null;
  date_of_joining: string;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(await authHeader()),
    },
    body: JSON.stringify(body),
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
    throw new Error("Not signed in");
  }
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json() as Promise<T>;
}

export function fetchMe(): Promise<MeOut> {
  return apiGet<MeOut>("/me");
}

export function fetchDirectoryMeta(): Promise<DirectoryMeta> {
  return apiGet<DirectoryMeta>("/employees/meta");
}

export function createEmployee(payload: EmployeeCreate): Promise<EmployeeDetail> {
  return apiPost<EmployeeDetail>("/employees", payload);
}

export type EmployeeUpdate = Partial<{
  first_name: string;
  middle_name: string | null;
  last_name: string | null;
  phone: string;
  gender: string | null;
  date_of_birth: string | null;
  designation: string;
  department: string;
  division: string;
  branch: string;
  circle_id: number;
  reporting_manager_id: number | null;
  date_of_joining: string;
  date_of_leaving: string | null;
  fathers_name: string | null;
  mothers_name: string | null;
  marital_status: string | null;
  spouse_name: string | null;
  alternate_phone: string | null;
  pan_no: string | null;
  aadhaar_no: string | null;
}>;

export async function updateEmployee(
  employeeId: number,
  payload: EmployeeUpdate,
): Promise<EmployeeDetail> {
  const res = await fetch(`${API_BASE}/employees/${employeeId}`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(await authHeader()),
    },
    body: JSON.stringify(payload),
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
    throw new Error("Not signed in");
  }
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json() as Promise<EmployeeDetail>;
}

export type OrgKind = "department" | "division" | "branch" | "designation";

export interface OrgMaster {
  id: string;
  kind: OrgKind;
  name: string;
  raw_values: string[];
  employee_count: number;
}

export function fetchOrgMasters(kind?: OrgKind): Promise<OrgMaster[]> {
  return apiGet<OrgMaster[]>(`/org/masters${kind ? `?kind=${kind}` : ""}`);
}

export function createOrgMaster(kind: OrgKind, name: string): Promise<OrgMaster> {
  return apiPost<OrgMaster>("/org/masters", { kind, name });
}

export async function renameOrgMaster(id: string, name: string): Promise<OrgMaster> {
  const res = await fetch(`${API_BASE}/org/masters/${id}`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(await authHeader()),
    },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json() as Promise<OrgMaster>;
}

export function mergeOrgMaster(id: string, intoId: string): Promise<OrgMaster> {
  return apiPost<OrgMaster>(`/org/masters/${id}/merge`, { into_master_id: intoId });
}

export function fetchEmployees(params: {
  q?: string;
  department?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<EmployeeListOut> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.department) qs.set("department", params.department);
  if (params.status) qs.set("status", params.status);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  const suffix = qs.size ? `?${qs}` : "";
  return apiGet<EmployeeListOut>(`/employees${suffix}`);
}

export interface HistoryEntry {
  category: "job" | "personal" | "compensation";
  field: string;
  old_value: string | null;
  new_value: string | null;
  effective_date: string;
  changed_by: number | null;
  created_at: string;
}

export function fetchEmployeeHistory(employeeId: number): Promise<HistoryEntry[]> {
  return apiGet<HistoryEntry[]>(`/employees/${employeeId}/history`);
}

export interface LetterType {
  key: string;
  label: string;
  needs_ctc: boolean;
}
export function fetchLetterTypes(): Promise<LetterType[]> {
  return apiGet<LetterType[]>("/letters/types");
}

export interface Band {
  id: string;
  code: string;
  name: string;
  level: number;
  min_ctc: string;
  max_ctc: string;
}
export interface EmployeeBand {
  employee_id: number;
  band_id: string | null;
  band_code: string | null;
  band_name: string | null;
  min_ctc: string | null;
  max_ctc: string | null;
  current_ctc: string | null;
  fit: "within" | "below" | "above" | null;
}
export function fetchBands(): Promise<Band[]> {
  return apiGet<Band[]>("/bands");
}
export function createBand(body: {
  code: string;
  name: string;
  level: number;
  min_ctc: string;
  max_ctc: string;
}): Promise<Band> {
  return apiPost<Band>("/bands", body);
}
export function assignBand(employeeId: number, bandId: string): Promise<EmployeeBand> {
  return apiPost<EmployeeBand>("/bands/assign", { employee_id: employeeId, band_id: bandId });
}
export function fetchEmployeeBand(employeeId: number): Promise<EmployeeBand> {
  return apiGet<EmployeeBand>(`/bands/employee/${employeeId}`);
}

export function fetchEmployee(employeeId: string): Promise<EmployeeDetail> {
  return apiGet<EmployeeDetail>(`/employees/${employeeId}`);
}

// ----------------------------------------------------------------- control plane

export interface Plan {
  code: string;
  name: string;
  price_per_employee: string;
  included_employees: number;
  features: Record<string, unknown>;
}
export interface Tenant {
  id: string;
  name: string;
  plan_code: string | null;
  status: string;
  region: string;
  employee_count: number;
  mrr: string;
}
export interface Invoice {
  id: string;
  tenant_id: string;
  period_year: number;
  period_month: number;
  employee_count: number;
  rate: string;
  amount: string;
  status: string;
}
export interface StatutoryPack {
  id: string;
  name: string;
  country: string;
  effective_from: string;
  rates: Record<string, unknown>;
  is_active: boolean;
}
export interface PlatformInsights {
  tenants: number;
  active_tenants: number;
  billable_employees: number;
  mrr: string;
}

export function fetchPlans(): Promise<Plan[]> {
  return apiGet<Plan[]>("/control-plane/plans");
}
export function fetchTenants(): Promise<Tenant[]> {
  return apiGet<Tenant[]>("/control-plane/tenants");
}
export function createTenant(body: {
  id: string;
  name: string;
  plan_code: string;
  region?: string;
}): Promise<Tenant> {
  return apiPost<Tenant>("/control-plane/tenants", body);
}
export function setTenantStatus(id: string, status: string): Promise<Tenant> {
  return apiPatch<Tenant>(`/control-plane/tenants/${id}`, { status });
}
export function runBilling(year: number, month: number): Promise<Invoice[]> {
  return apiPost<Invoice[]>("/control-plane/billing/run", {
    period_year: year,
    period_month: month,
  });
}
export function fetchInvoices(): Promise<Invoice[]> {
  return apiGet<Invoice[]>("/control-plane/invoices");
}
export function fetchStatutoryPacks(): Promise<StatutoryPack[]> {
  return apiGet<StatutoryPack[]>("/control-plane/statutory-packs");
}
export function fetchPlatformInsights(): Promise<PlatformInsights> {
  return apiGet<PlatformInsights>("/control-plane/insights");
}

export interface Announcement {
  id: string;
  title: string;
  body: string;
  level: "info" | "success" | "warning";
  created_at: string;
}
export function fetchAnnouncements(): Promise<Announcement[]> {
  return apiGet<Announcement[]>("/control-plane/announcements");
}
export function postAnnouncement(body: {
  title: string;
  body: string;
  level: string;
}): Promise<Announcement> {
  return apiPost<Announcement>("/control-plane/announcements", body);
}
export async function retractAnnouncement(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/control-plane/announcements/${id}`, {
    method: "DELETE",
    headers: { ...(await authHeader()) },
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Retract failed (${res.status})`);
  }
}

// ----------------------------------------------------------------- reports

export interface ReportMeta {
  id: string;
  name: string;
  description: string;
  columns: string[];
}
export interface ReportData {
  id: string;
  name: string;
  columns: string[];
  rows: Record<string, unknown>[];
}
export interface Insights {
  headcount: number;
  exits_total: number;
  latest_monthly_net: string | null;
  avg_tenure_months: number | null;
  open_requisitions: number;
}

export function fetchReports(): Promise<ReportMeta[]> {
  return apiGet<ReportMeta[]>("/reports");
}
export function fetchInsights(): Promise<Insights> {
  return apiGet<Insights>("/reports/insights");
}
export function runReport(id: string): Promise<ReportData> {
  return apiGet<ReportData>(`/reports/${id}`);
}

// ----------------------------------------------------------------- exit / F&F

export interface ClearanceItem {
  id: string;
  item: string;
  status: string;
  note: string | null;
}

export interface FnFSettlement {
  pending_salary: string;
  gratuity: string;
  leave_encashment: string;
  notice_recovery: string;
  other_recoveries: string;
  net_settlement: string;
  status: string;
}

export interface ExitCase {
  id: string;
  employee_id: number;
  employee_name: string;
  resignation_date: string;
  last_working_day: string;
  reason: string | null;
  notice_required_days: number;
  status: string;
  clearance: ClearanceItem[];
  fnf: FnFSettlement | null;
}

export function fetchExitCases(): Promise<ExitCase[]> {
  return apiGet<ExitCase[]>("/exit/cases");
}
export function initiateExit(body: {
  employee_id: number;
  resignation_date: string;
  last_working_day: string;
  reason?: string;
  notice_required_days: number;
}): Promise<ExitCase> {
  return apiPost<ExitCase>("/exit/cases", body);
}
export function clearItem(caseId: string, itemId: string): Promise<ExitCase> {
  return apiPost<ExitCase>(`/exit/cases/${caseId}/clearance/${itemId}`, {});
}
export function computeFnf(caseId: string): Promise<ExitCase> {
  return apiPost<ExitCase>(`/exit/cases/${caseId}/compute-fnf`, {});
}
export function approveFnf(caseId: string): Promise<ExitCase> {
  return apiPost<ExitCase>(`/exit/cases/${caseId}/fnf/approve`, {});
}
export function payFnf(caseId: string): Promise<ExitCase> {
  return apiPost<ExitCase>(`/exit/cases/${caseId}/fnf/pay`, {});
}

// ---- exit depth: KT checklist, interview, alumni, analytics

export interface KtItem {
  id: string;
  task: string;
  assignee: string | null;
  status: "pending" | "done";
  note: string | null;
}
export function fetchKt(caseId: string): Promise<KtItem[]> {
  return apiGet<KtItem[]>(`/exit/cases/${caseId}/kt`);
}
export function seedKt(caseId: string): Promise<KtItem[]> {
  return apiPost<KtItem[]>(`/exit/cases/${caseId}/kt/seed-defaults`, {});
}
export function addKt(caseId: string, task: string, assignee?: string): Promise<KtItem[]> {
  return apiPost<KtItem[]>(`/exit/cases/${caseId}/kt`, { task, assignee: assignee ?? null });
}
export function toggleKt(caseId: string, itemId: string): Promise<KtItem[]> {
  return apiPost<KtItem[]>(`/exit/cases/${caseId}/kt/${itemId}/toggle`, {});
}

export interface ExitInterview {
  primary_reason: string | null;
  would_recommend: boolean | null;
  rating_management: number | null;
  rating_role: number | null;
  rating_culture: number | null;
  feedback: string | null;
  conducted_on: string | null;
}
export function fetchInterview(caseId: string): Promise<ExitInterview | null> {
  return apiGet<ExitInterview | null>(`/exit/cases/${caseId}/interview`);
}
export function saveInterview(
  caseId: string,
  body: Partial<ExitInterview>,
): Promise<ExitInterview> {
  return apiPut<ExitInterview>(`/exit/cases/${caseId}/interview`, body);
}

export interface Alumnus {
  id: string;
  employee_id: number;
  employee_name: string;
  eligible_for_rehire: boolean;
  personal_email: string | null;
  note: string | null;
  last_working_day: string | null;
}
export function fetchAlumni(): Promise<Alumnus[]> {
  return apiGet<Alumnus[]>("/exit/alumni");
}
export function upsertAlumni(body: {
  employee_id: number;
  eligible_for_rehire: boolean;
  personal_email?: string | null;
  note?: string | null;
}): Promise<Alumnus> {
  return apiPost<Alumnus>("/exit/alumni", body);
}

export interface ExitAnalytics {
  total_exits: number;
  by_reason: Record<string, number>;
  by_month: Record<string, number>;
  avg_tenure_days: number;
  attrition_rate_pct: string;
}
export function fetchExitAnalytics(): Promise<ExitAnalytics> {
  return apiGet<ExitAnalytics>("/exit/analytics");
}

// ----------------------------------------------------------------- performance

export interface ReviewCycle {
  id: string;
  name: string;
  period_year: number;
  status: string;
  review_count: number;
}

export interface Review {
  id: string;
  cycle_id: string;
  employee_id: number;
  employee_name: string;
  self_rating: number | null;
  manager_rating: number | null;
  potential: number | null;
  final_rating: number | null;
  status: string;
  nine_box: number | null;
  nine_box_label: string | null;
  can_self: boolean;
  can_manage: boolean;
}

export interface Increment {
  id: string;
  employee_id: number;
  current_ctc: string;
  proposed_ctc: string;
  pct: string;
  effective_date: string;
  status: string;
}

export interface Goal {
  id: string;
  employee_id: number;
  title: string;
  description: string | null;
  progress: number;
  status: string;
}

export function fetchCycles(): Promise<ReviewCycle[]> {
  return apiGet<ReviewCycle[]>("/performance/cycles");
}
export function createCycle(name: string, periodYear: number): Promise<ReviewCycle> {
  return apiPost<ReviewCycle>("/performance/cycles", { name, period_year: periodYear });
}
export function enrollCycle(id: string): Promise<ReviewCycle> {
  return apiPost<ReviewCycle>(`/performance/cycles/${id}/enroll`, {});
}
export function fetchCycleReviews(id: string): Promise<Review[]> {
  return apiGet<Review[]>(`/performance/cycles/${id}/reviews`);
}
export function fetchMyReviews(): Promise<Review[]> {
  return apiGet<Review[]>("/performance/reviews/mine");
}
export function submitSelfReview(id: string, rating: number, comment?: string): Promise<Review> {
  return apiPost<Review>(`/performance/reviews/${id}/self`, {
    self_rating: rating,
    self_comment: comment ?? null,
  });
}
export function submitManagerReview(
  id: string,
  rating: number,
  potential: number,
  comment?: string,
): Promise<Review> {
  return apiPost<Review>(`/performance/reviews/${id}/manager`, {
    manager_rating: rating,
    potential,
    manager_comment: comment ?? null,
  });
}
export function publishReview(id: string, finalRating?: number): Promise<Review> {
  return apiPost<Review>(`/performance/reviews/${id}/publish`, {
    final_rating: finalRating ?? null,
  });
}
export function proposeIncrement(reviewId: string): Promise<Increment> {
  return apiPost<Increment>(`/performance/reviews/${reviewId}/increment`, {});
}
export function approveIncrement(id: string): Promise<Increment> {
  return apiPost<Increment>(`/performance/increments/${id}/approve`, {});
}
export function pushIncrement(id: string): Promise<Increment> {
  return apiPost<Increment>(`/performance/increments/${id}/push`, {});
}
export function fetchGoals(): Promise<Goal[]> {
  return apiGet<Goal[]>("/performance/goals");
}
export function addGoal(title: string, description?: string): Promise<Goal> {
  return apiPost<Goal>("/performance/goals", { title, description: description ?? null });
}
export function updateGoal(id: string, progress: number, status?: string): Promise<Goal> {
  return apiPatch<Goal>(`/performance/goals/${id}`, { progress, status: status ?? null });
}

async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(await authHeader()),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json() as Promise<T>;
}

// ----------------------------------------------------------------- recruitment

export interface Requisition {
  id: string;
  code: string;
  title: string;
  department: string | null;
  location: string | null;
  openings: number;
  status: string;
  candidate_count: number;
}

export interface Candidate {
  id: string;
  requisition_id: string;
  name: string;
  email: string;
  phone: string | null;
  source: string;
  stage: string;
  rating: number | null;
  bgv_status: string;
  note: string | null;
  onboarded_employee_id: number | null;
}

export interface Offer {
  id: string;
  candidate_id: string;
  designation: string;
  department: string;
  ctc_annual: string;
  joining_date: string;
  status: string;
}

export function fetchRequisitions(): Promise<Requisition[]> {
  return apiGet<Requisition[]>("/recruitment/requisitions");
}
export function createRequisition(body: {
  code: string;
  title: string;
  department?: string;
  location?: string;
  openings: number;
}): Promise<Requisition> {
  return apiPost<Requisition>("/recruitment/requisitions", body);
}
export function fetchCandidates(requisitionId: string): Promise<Candidate[]> {
  return apiGet<Candidate[]>(`/recruitment/candidates?requisition_id=${requisitionId}`);
}
export function addCandidate(body: {
  requisition_id: string;
  name: string;
  email: string;
  phone?: string;
}): Promise<Candidate> {
  return apiPost<Candidate>("/recruitment/candidates", body);
}
export function moveStage(cid: string, stage: string): Promise<Candidate> {
  return apiPost<Candidate>(`/recruitment/candidates/${cid}/stage`, { stage });
}
export function makeOffer(
  cid: string,
  body: { designation: string; department: string; ctc_annual: number; joining_date: string },
): Promise<Offer> {
  return apiPost<Offer>(`/recruitment/candidates/${cid}/offer`, body);
}
export function acceptOffer(cid: string): Promise<Offer> {
  return apiPost<Offer>(`/recruitment/candidates/${cid}/offer/accept`, {});
}
export function onboardCandidate(
  cid: string,
  body: { employee_code: string; division: string; branch: string; circle_id: number },
): Promise<{ candidate_id: string; employee_id: number; employee_code: string }> {
  return apiPost(`/recruitment/candidates/${cid}/onboard`, body);
}

// ----------------------------------------------------------------- timesheet

export interface Project {
  id: string;
  code: string;
  name: string;
  client: string | null;
}

export interface TimesheetWeek {
  employee_id: number;
  week_start: string;
  dates: string[];
  status: string;
  entries: { project_id: string; work_date: string; hours: string }[];
  total_hours: string;
  overtime: string;
  approver_name: string | null;
  decision_note: string | null;
  can_decide: boolean;
}

export function fetchProjects(): Promise<Project[]> {
  return apiGet<Project[]>("/timesheet/projects");
}

export function fetchWeek(weekOf: string, employeeId?: number): Promise<TimesheetWeek> {
  const e = employeeId ? `&employee_id=${employeeId}` : "";
  return apiGet<TimesheetWeek>(`/timesheet/week?week_of=${weekOf}${e}`);
}

export function logHours(
  projectId: string,
  workDate: string,
  hours: number,
): Promise<TimesheetWeek> {
  return apiPost<TimesheetWeek>("/timesheet/entries", {
    project_id: projectId,
    work_date: workDate,
    hours,
  });
}

export function submitWeek(weekOf: string): Promise<TimesheetWeek> {
  return apiPost<TimesheetWeek>(`/timesheet/week/submit?week_of=${weekOf}`, {});
}

export function decideWeek(
  action: "approve" | "reject",
  employeeId: number,
  weekOf: string,
  note?: string,
): Promise<TimesheetWeek> {
  return apiPost<TimesheetWeek>(`/timesheet/week/${action}`, {
    employee_id: employeeId,
    week_of: weekOf,
    note: note ?? null,
  });
}

// ----------------------------------------------------------------- attendance

export interface AttendanceSummary {
  employee_id: number;
  year: number;
  month: number;
  days: { day: string; status: string }[];
  present: number;
  wfh: number;
  leave: number;
  holiday: number;
  weekend: number;
  absent: number;
  not_marked: number;
  upcoming: number;
  lop: number;
  payable: number;
}

export function fetchAttendance(
  year: number,
  month: number,
  employeeId?: number,
): Promise<AttendanceSummary> {
  const e = employeeId ? `&employee_id=${employeeId}` : "";
  return apiGet<AttendanceSummary>(
    `/attendance/summary?year=${year}&month=${month}${e}`,
  );
}

export function markAttendance(
  employeeId: number,
  workDate: string,
  status: "present" | "absent" | "wfh",
): Promise<AttendanceSummary> {
  return apiPost<AttendanceSummary>("/attendance", {
    employee_id: employeeId,
    work_date: workDate,
    status,
  });
}

// ----------------------------------------------------------------- feedback

export interface Feedback {
  id: string;
  from_employee_id: number;
  from_name: string | null;
  to_employee_id: number;
  to_name: string | null;
  kind: "feedback" | "recognition";
  badge: string | null;
  visibility: "private" | "public";
  message: string;
  created_at: string;
}

export function fetchBadges(): Promise<string[]> {
  return apiGet<string[]>("/feedback/badges");
}
export function giveFeedback(body: {
  to_employee_id: number;
  kind: "feedback" | "recognition";
  badge?: string | null;
  visibility: "private" | "public";
  message: string;
}): Promise<Feedback> {
  return apiPost<Feedback>("/feedback", body);
}
export function fetchReceived(employeeId?: number): Promise<Feedback[]> {
  return apiGet<Feedback[]>(`/feedback/received${employeeId ? `?employee_id=${employeeId}` : ""}`);
}
export function fetchGiven(): Promise<Feedback[]> {
  return apiGet<Feedback[]>("/feedback/given");
}
export function fetchWall(): Promise<Feedback[]> {
  return apiGet<Feedback[]>("/feedback/wall");
}

// ----------------------------------------------------------------- claims

export interface Claim {
  id: string;
  employee_id: number;
  employee_name: string | null;
  category: string;
  description: string;
  claim_date: string;
  amount: string;
  receipt_ref: string | null;
  status: "pending" | "approved" | "rejected" | "paid";
}
export function fetchClaimCategories(): Promise<string[]> {
  return apiGet<string[]>("/claims/categories");
}
export function fetchClaims(scope: "mine" | "pending" = "mine"): Promise<Claim[]> {
  return apiGet<Claim[]>(`/claims?scope=${scope}`);
}
export function fileClaim(body: {
  category: string;
  description: string;
  claim_date: string;
  amount: string;
  receipt_ref?: string | null;
}): Promise<Claim> {
  return apiPost<Claim>("/claims", body);
}
export function decideClaim(id: string, action: "approve" | "reject"): Promise<Claim> {
  return apiPost<Claim>(`/claims/${id}/${action}`, {});
}

// ----------------------------------------------------------------- policies

export interface Policy {
  id: string;
  title: string;
  category: string;
  body: string;
  version: number;
  published_at: string;
  acknowledged: boolean;
}
export interface PolicyCompliance {
  policy_id: string;
  title: string;
  acknowledged: number;
  headcount: number;
  pending: number;
}
export function fetchPolicies(): Promise<Policy[]> {
  return apiGet<Policy[]>("/policies");
}
export function publishPolicy(body: {
  title: string;
  category: string;
  body: string;
  version: number;
}): Promise<Policy> {
  return apiPost<Policy>("/policies", body);
}
export function ackPolicy(id: string): Promise<Policy> {
  return apiPost<Policy>(`/policies/${id}/ack`, {});
}
export function fetchPolicyCompliance(id: string): Promise<PolicyCompliance> {
  return apiGet<PolicyCompliance>(`/policies/${id}/compliance`);
}

// ----------------------------------------------------------------- helpdesk

export interface Ticket {
  id: string;
  employee_id: number;
  employee_name: string | null;
  category: string;
  subject: string;
  description: string;
  priority: "low" | "medium" | "high";
  status: "open" | "in_progress" | "resolved" | "closed";
  assignee_id: number | null;
  assignee_name: string | null;
  resolution: string | null;
  created_at: string;
  resolved_at: string | null;
}
export function fetchTicketCategories(): Promise<string[]> {
  return apiGet<string[]>("/tickets/categories");
}
export function fetchTickets(scope: "mine" | "assigned" | "all" = "mine"): Promise<Ticket[]> {
  return apiGet<Ticket[]>(`/tickets?scope=${scope}`);
}
export function raiseTicket(body: {
  category: string;
  subject: string;
  description: string;
  priority: string;
}): Promise<Ticket> {
  return apiPost<Ticket>("/tickets", body);
}
export function assignTicket(id: string, assigneeId: number): Promise<Ticket> {
  return apiPost<Ticket>(`/tickets/${id}/assign`, { assignee_id: assigneeId });
}
export function setTicketStatus(id: string, status: string, resolution?: string): Promise<Ticket> {
  return apiPost<Ticket>(`/tickets/${id}/status`, { status, resolution: resolution ?? null });
}

// ----------------------------------------------------------------- duty (OOD/WFH)

export interface Duty {
  id: string;
  employee_id: number;
  employee_name: string | null;
  duty_type: "wfh" | "on_duty";
  start_date: string;
  end_date: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
}
export function fetchDuty(scope: "mine" | "pending" = "mine"): Promise<Duty[]> {
  return apiGet<Duty[]>(`/duty?scope=${scope}`);
}
export function requestDuty(body: {
  duty_type: "wfh" | "on_duty";
  start_date: string;
  end_date: string;
  reason: string;
}): Promise<Duty> {
  return apiPost<Duty>("/duty", body);
}
export function decideDuty(id: string, action: "approve" | "reject"): Promise<Duty> {
  return apiPost<Duty>(`/duty/${id}/${action}`, {});
}

// ----------------------------------------------------------------- pip

export interface PipCheckpoint {
  id: string;
  checkpoint_date: string;
  rating: "on_track" | "at_risk" | "off_track";
  note: string | null;
  created_at: string;
}
export interface Pip {
  id: string;
  employee_id: number;
  employee_name: string | null;
  manager_id: number | null;
  reason: string;
  objectives: string;
  start_date: string;
  end_date: string;
  status: "active" | "improved" | "extended" | "terminated" | "closed";
  suggested_checkpoints: string[];
  checkpoints: PipCheckpoint[];
}
export function fetchPips(scope: "managed" | "mine" = "managed"): Promise<Pip[]> {
  return apiGet<Pip[]>(`/pip?scope=${scope}`);
}
export function openPip(body: {
  employee_id: number;
  reason: string;
  objectives: string;
  start_date: string;
  end_date: string;
}): Promise<Pip> {
  return apiPost<Pip>("/pip", body);
}
export function addPipCheckpoint(
  id: string,
  rating: string,
  note?: string,
): Promise<Pip> {
  return apiPost<Pip>(`/pip/${id}/checkpoint`, { rating, note: note ?? null });
}
export function closePip(id: string, outcome: string): Promise<Pip> {
  return apiPost<Pip>(`/pip/${id}/close`, { outcome });
}

// ----------------------------------------------------------------- check-ins

export interface CheckIn {
  id: string;
  employee_id: number;
  employee_name: string | null;
  check_in_date: string;
  highlights: string;
  challenges: string | null;
  mood: number;
  mood_label: string;
  created_at: string;
}
export function logCheckIn(body: {
  highlights: string;
  challenges?: string | null;
  mood: number;
}): Promise<CheckIn> {
  return apiPost<CheckIn>("/check-ins", body);
}
export function fetchMyCheckIns(): Promise<CheckIn[]> {
  return apiGet<CheckIn[]>("/check-ins/mine");
}
export function fetchTeamCheckIns(): Promise<CheckIn[]> {
  return apiGet<CheckIn[]>("/check-ins/team");
}

// ----------------------------------------------------------------- shifts

export interface Shift {
  id: string;
  code: string;
  name: string;
  start_time: string;
  end_time: string;
  break_minutes: number;
  is_night: boolean;
  hours: string;
}
export interface RosterRow {
  employee_id: number;
  employee_name: string;
  shift_code: string | null;
  shift_name: string | null;
}

export function fetchShifts(): Promise<Shift[]> {
  return apiGet<Shift[]>("/shifts");
}
export function createShift(body: {
  code: string;
  name: string;
  start_time: string;
  end_time: string;
  break_minutes: number;
}): Promise<Shift> {
  return apiPost<Shift>("/shifts", body);
}
export function fetchRoster(on?: string): Promise<RosterRow[]> {
  return apiGet<RosterRow[]>(`/shifts/roster${on ? `?on=${on}` : ""}`);
}
export function assignShift(
  employeeId: number,
  shiftId: string,
  effectiveFrom?: string,
): Promise<{ status: string }> {
  return apiPost(`/shifts/assign`, {
    employee_id: employeeId,
    shift_id: shiftId,
    effective_from: effectiveFrom ?? null,
  });
}
export function fetchMyShift(): Promise<RosterRow | null> {
  return apiGet<RosterRow | null>("/shifts/my");
}

export interface Regularization {
  id: string;
  employee_id: number;
  employee_name: string | null;
  work_date: string;
  requested_status: "present" | "wfh";
  reason: string;
  status: "pending" | "approved" | "rejected";
  decision_note: string | null;
}

export function fetchRegularizations(
  scope: "mine" | "pending" = "mine",
): Promise<Regularization[]> {
  return apiGet<Regularization[]>(`/attendance/regularizations?scope=${scope}`);
}
export function requestRegularization(body: {
  work_date: string;
  requested_status: "present" | "wfh";
  reason: string;
}): Promise<Regularization> {
  return apiPost<Regularization>("/attendance/regularizations", body);
}
export function decideRegularization(
  id: string,
  action: "approve" | "reject",
  note?: string,
): Promise<Regularization> {
  return apiPost<Regularization>(`/attendance/regularizations/${id}/${action}`, {
    note: note ?? null,
  });
}

export interface Overtime {
  id: string;
  employee_id: number;
  employee_name: string | null;
  ot_date: string;
  hours: string;
  rate_multiplier: string;
  reason: string;
  status: "pending" | "approved" | "rejected" | "paid";
}
export function fetchOvertime(scope: "mine" | "pending" = "mine"): Promise<Overtime[]> {
  return apiGet<Overtime[]>(`/overtime?scope=${scope}`);
}
export function logOvertime(body: {
  ot_date: string;
  hours: string;
  rate_multiplier?: string;
  reason: string;
}): Promise<Overtime> {
  return apiPost<Overtime>("/overtime", body);
}
export function decideOvertime(id: string, action: "approve" | "reject"): Promise<Overtime> {
  return apiPost<Overtime>(`/overtime/${id}/${action}`, {});
}

export interface CompOff {
  id: string;
  employee_id: number;
  employee_name: string | null;
  earned_date: string;
  reason: string;
  status: "pending" | "approved" | "rejected" | "availed" | "expired";
  expiry_date: string | null;
  availed_on: string | null;
}
export function fetchCompOff(
  scope: "mine" | "pending" | "available" = "mine",
): Promise<CompOff[]> {
  return apiGet<CompOff[]>(`/comp-off?scope=${scope}`);
}
export function earnCompOff(body: { earned_date: string; reason: string }): Promise<CompOff> {
  return apiPost<CompOff>("/comp-off", body);
}
export function decideCompOff(id: string, action: "approve" | "reject"): Promise<CompOff> {
  return apiPost<CompOff>(`/comp-off/${id}/${action}`, {});
}
export function availCompOff(id: string, availDate: string): Promise<CompOff> {
  return apiPost<CompOff>(`/comp-off/${id}/avail`, { avail_date: availDate });
}

// ------------------------------------------------------------ salary config

export type ComponentType = "earning" | "reimbursement" | "deduction" | "employer";
export type CalcType = "fixed" | "pct_ctc" | "pct_basic" | "pct_gross" | "balancing";

export interface SalaryComponent {
  id: string;
  code: string;
  name: string;
  component_type: ComponentType;
  calc_type: CalcType;
  value: string;
  tax_treatment: "taxable" | "partial" | "exempt";
  pf_wage: boolean;
  esi_wage: boolean;
  pt_wage: boolean;
  on_payslip: boolean;
}
export interface SalaryConfigPreviewLine {
  code: string;
  name: string;
  amount: string;
}
export interface SalaryConfigPreview {
  ctc_annual: string;
  monthly_ctc: string;
  lines: SalaryConfigPreviewLine[];
  gross_monthly: string;
}

export function fetchSalaryComponents(): Promise<SalaryComponent[]> {
  return apiGet<SalaryComponent[]>("/salary-config/components");
}
export function createSalaryComponent(body: {
  code: string;
  name: string;
  component_type: ComponentType;
  calc_type: CalcType;
  value: string;
  tax_treatment?: "taxable" | "partial" | "exempt";
  pf_wage?: boolean;
  esi_wage?: boolean;
  pt_wage?: boolean;
  sort_order?: number;
}): Promise<SalaryComponent> {
  return apiPost<SalaryComponent>("/salary-config/components", body);
}
export async function deactivateSalaryComponent(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/salary-config/components/${id}`, {
    method: "DELETE",
    headers: { ...(await authHeader()) },
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Delete failed (${res.status})`);
  }
}
export function previewSalaryStructure(ctcAnnual: string): Promise<SalaryConfigPreview> {
  return apiGet<SalaryConfigPreview>(
    `/salary-config/preview?ctc_annual=${encodeURIComponent(ctcAnnual)}`,
  );
}

// -------------------------------------------------- employee 360 records

export interface FamilyMember {
  id: string;
  relation: string;
  full_name: string;
  date_of_birth: string | null;
  gender: string | null;
  is_dependent: boolean;
  is_nominee: boolean;
  nominee_share: string;
  contact: string | null;
}
export interface Education {
  id: string;
  degree: string;
  specialization: string | null;
  institution: string | null;
  year_completed: number | null;
  grade: string | null;
}
export interface Experience {
  id: string;
  employer: string;
  designation: string | null;
  from_date: string | null;
  to_date: string | null;
  summary: string | null;
}
export interface Award {
  id: string;
  title: string;
  category: string | null;
  awarded_on: string | null;
  citation: string | null;
}
export interface Training {
  id: string;
  program: string;
  provider: string | null;
  status: "planned" | "in_progress" | "completed" | "cancelled";
  completed_on: string | null;
}
export interface Incident {
  id: string;
  kind: "disciplinary" | "accident";
  incident_date: string;
  category: string | null;
  severity: "low" | "medium" | "high";
  description: string;
  action_taken: string | null;
  status: "open" | "closed";
}
export interface SpecialDate {
  label: string;
  on: string;
  in_days: number;
  years: number | null;
}
export interface EmployeeRecords {
  employee_id: number;
  family: FamilyMember[];
  education: Education[];
  experience: Experience[];
  awards: Award[];
  training: Training[];
  incidents: Incident[];
  special_dates: SpecialDate[];
  nominee_total: string;
}
export type RecordResource =
  | "family"
  | "education"
  | "experience"
  | "awards"
  | "training"
  | "incidents";

export function fetchEmployeeRecords(employeeId: number): Promise<EmployeeRecords> {
  return apiGet<EmployeeRecords>(`/employees/${employeeId}/records`);
}
export function addEmployeeRecord<T>(
  employeeId: number,
  resource: RecordResource,
  body: Record<string, unknown>,
): Promise<T> {
  return apiPost<T>(`/employees/${employeeId}/${resource}`, body);
}
export async function deleteEmployeeRecord(
  employeeId: number,
  resource: RecordResource,
  recordId: string,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/employees/${employeeId}/records/${resource}/${recordId}`,
    { method: "DELETE", headers: { ...(await authHeader()) } },
  );
  if (!res.ok && res.status !== 204) {
    throw new Error(`Delete failed (${res.status})`);
  }
}

// ----------------------------------------------------------------- payroll

export interface StructurePreview {
  ctc_annual: string;
  basic: string;
  hra: string;
  special_allowance: string;
  gross_monthly: string;
}

export interface StructureSaved extends StructurePreview {
  employee_id: number;
  tax_regime: string;
  monthly_tds: string;
}

export interface PayrollRun {
  id: string;
  period_year: number;
  period_month: number;
  working_days: number;
  status: string;
  employee_count: number;
  total_gross: string;
  total_net: string;
}

export interface Payslip {
  employee_id: number;
  employee_name: string;
  period_year: number;
  period_month: number;
  lop_days: string;
  earnings: Record<string, string>;
  deductions: Record<string, string>;
  employer_contributions: Record<string, string>;
  gross: string;
  total_deductions: string;
  net_pay: string;
}

export function previewStructure(ctcAnnual: number): Promise<StructurePreview> {
  return apiGet<StructurePreview>(`/payroll/preview?ctc_annual=${ctcAnnual}`);
}

export function fetchStructure(employeeId: number): Promise<StructureSaved> {
  return apiGet<StructureSaved>(`/payroll/structures/${employeeId}`);
}

export interface Arrear {
  id: string;
  employee_id: number;
  employee_name: string | null;
  amount: string;
  months: number;
  reason: string | null;
  effective_from: string;
  status: "pending" | "paid" | "cancelled";
}
export function fetchArrears(employeeId?: number): Promise<Arrear[]> {
  return apiGet<Arrear[]>(`/payroll/arrears${employeeId ? `?employee_id=${employeeId}` : ""}`);
}

export interface StatutoryIds {
  employee_id: number;
  uan: string | null;
  pf_number: string | null;
  esic_ip: string | null;
  pt_state: string;
}
export function fetchStatutoryIds(employeeId: number): Promise<StatutoryIds> {
  return apiGet<StatutoryIds>(`/payroll/statutory/${employeeId}`);
}
export function setStatutoryIds(
  employeeId: number,
  body: { uan?: string | null; pf_number?: string | null; esic_ip?: string | null; pt_state: string },
): Promise<StatutoryIds> {
  return apiPut<StatutoryIds>(`/payroll/statutory/${employeeId}`, body);
}

export function fetchEmployeePayslips(employeeId: number): Promise<Payslip[]> {
  return apiGet<Payslip[]>(`/payroll/payslips/${employeeId}`);
}

export async function setStructure(
  employeeId: number,
  ctcAnnual: number,
  effectiveFrom: string,
  taxRegime: "new" | "old" = "new",
  chapterViaDeductions = 0,
): Promise<StructureSaved> {
  return apiPut(`/payroll/structures/${employeeId}`, {
    ctc_annual: ctcAnnual,
    effective_from: effectiveFrom,
    tax_regime: taxRegime,
    chapter_via_deductions: chapterViaDeductions,
  });
}

export function fetchRuns(): Promise<PayrollRun[]> {
  return apiGet<PayrollRun[]>("/payroll/runs");
}

export function createRun(
  year: number,
  month: number,
  workingDays: number,
): Promise<PayrollRun> {
  return apiPost<PayrollRun>("/payroll/runs", {
    period_year: year,
    period_month: month,
    working_days: workingDays,
  });
}

export function finalizeRun(id: string): Promise<PayrollRun> {
  return apiPost<PayrollRun>(`/payroll/runs/${id}/finalize`, {});
}

export function markRunPaid(id: string): Promise<PayrollRun> {
  return apiPost<PayrollRun>(`/payroll/runs/${id}/mark-paid`, {});
}

export interface StatutoryTotals {
  pf_employee: string;
  pf_employer: string;
  esi_employee: string;
  esi_employer: string;
  pt: string;
  tds: string;
}

export function fetchStatutory(runId: string): Promise<StatutoryTotals> {
  return apiGet<StatutoryTotals>(`/payroll/runs/${runId}/statutory`);
}

/** Fetch a file endpoint with auth and trigger a browser download. */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...(await authHeader()) },
  });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function fetchRegister(runId: string): Promise<Payslip[]> {
  return apiGet<Payslip[]>(`/payroll/runs/${runId}/register`);
}

async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(await authHeader()),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json() as Promise<T>;
}

// ----------------------------------------------------------------- dashboard

export interface DashboardSummary {
  headcount: {
    total: number;
    active: number;
    probation: number;
    joining: number;
    notice: number;
    inactive: number;
  };
  on_leave_today: { employee_name: string; leave_code: string; end_date: string }[];
  my_pending_approvals: number;
  new_joiners: {
    full_name: string;
    designation: string | null;
    date_of_joining: string;
  }[];
  upcoming_holidays: { name: string; holiday_date: string }[];
}

export function fetchDashboard(): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>("/dashboard");
}

export interface PulseDecision {
  kind: string;
  severity: "high" | "medium" | "low";
  icon: string;
  title: string;
  detail: string;
  action_label: string;
  action_href: string;
  count: number;
}

export function fetchPulseInbox(): Promise<PulseDecision[]> {
  return apiGet<PulseDecision[]>("/pulse/inbox");
}

export interface Task {
  task_type:
    | "leave"
    | "timesheet"
    | "increment"
    | "regularization"
    | "overtime"
    | "comp_off"
    | "duty"
    | "claim";
  ref_id: string;
  employee_id: number;
  employee_name: string;
  title: string;
  subtitle: string;
  badge: string;
  can_reject: boolean;
  week_of: string | null;
}

export function fetchTasks(): Promise<Task[]> {
  return apiGet<Task[]>("/tasks");
}

// ----------------------------------------------------------------- assets

export interface Asset {
  id: string;
  asset_tag: string;
  category: string;
  name: string;
  serial_no: string | null;
  purchase_date: string | null;
  purchase_cost: string | null;
  status: "in_stock" | "assigned" | "retired" | "lost";
  condition: string;
  holder_id: number | null;
  holder_name: string | null;
  book_value: string | null;
}

export function fetchAssets(): Promise<Asset[]> {
  return apiGet<Asset[]>("/assets");
}
export function fetchEmployeeAssets(employeeId: number): Promise<Asset[]> {
  return apiGet<Asset[]>(`/assets/employee/${employeeId}`);
}

export interface DepreciationLine {
  id: string;
  asset_tag: string;
  name: string;
  category: string;
  purchase_cost: string;
  book_value: string;
  depreciated: string;
}
export interface DepreciationReport {
  lines: DepreciationLine[];
  total_cost: string;
  total_book_value: string;
  total_depreciated: string;
}
export function fetchDepreciation(): Promise<DepreciationReport> {
  return apiGet<DepreciationReport>("/assets/depreciation");
}
export function createAsset(body: {
  asset_tag: string;
  category: string;
  name: string;
  serial_no?: string | null;
  purchase_date?: string | null;
  purchase_cost?: string | null;
  condition?: string;
}): Promise<Asset> {
  return apiPost<Asset>("/assets", body);
}
export function assignAsset(
  assetId: string,
  employeeId: number,
  note?: string,
): Promise<Asset> {
  return apiPost<Asset>(`/assets/${assetId}/assign`, {
    employee_id: employeeId,
    note: note ?? null,
  });
}
export function returnAsset(
  assetId: string,
  condition?: string,
  note?: string,
): Promise<Asset> {
  return apiPost<Asset>(`/assets/${assetId}/return`, {
    condition: condition ?? null,
    note: note ?? null,
  });
}

// ----------------------------------------------------------------- advances

export interface Advance {
  id: string;
  employee_id: number;
  employee_name: string | null;
  kind: "advance" | "loan";
  principal_amount: string;
  emi_amount: string;
  outstanding: string;
  recovered: string;
  reason: string | null;
  status: "active" | "closed" | "cancelled";
  disbursed_on: string;
}

export function fetchAdvances(): Promise<Advance[]> {
  return apiGet<Advance[]>("/advances");
}
export function fetchEmployeeAdvances(employeeId: number): Promise<Advance[]> {
  return apiGet<Advance[]>(`/advances/employee/${employeeId}`);
}
export function issueAdvance(body: {
  employee_id: number;
  kind: string;
  principal_amount: string;
  emi_amount: string;
  reason?: string | null;
}): Promise<Advance> {
  return apiPost<Advance>("/advances", body);
}
export function cancelAdvance(id: string): Promise<Advance> {
  return apiPost<Advance>(`/advances/${id}/cancel`, {});
}

// ----------------------------------------------------------------- tax

export interface TaxSection {
  key: string;
  label: string;
  cap: string;
}
export interface TaxDeclItem {
  section: string;
  amount: string;
}
export interface TaxDeclaration {
  id: string | null;
  employee_id: number;
  fy: string;
  regime: "old" | "new";
  status: "draft" | "submitted" | "approved" | "rejected";
  items: TaxDeclItem[];
  declared_total: string;
  eligible_deduction: string;
  decided_at: string | null;
}
export interface PendingTaxDecl {
  id: string;
  employee_id: number;
  employee_name: string | null;
  fy: string;
  regime: string;
  eligible_deduction: string;
}

export function fetchTaxSections(): Promise<TaxSection[]> {
  return apiGet<TaxSection[]>("/tax/sections");
}
export function fetchTaxDeclaration(fy?: string): Promise<TaxDeclaration> {
  return apiGet<TaxDeclaration>(`/tax/declaration${fy ? `?fy=${fy}` : ""}`);
}
export function saveTaxDeclaration(body: {
  fy?: string;
  regime: "old" | "new";
  items: { section: string; amount: string }[];
}): Promise<TaxDeclaration> {
  return apiPut<TaxDeclaration>("/tax/declaration", body);
}
export function submitTaxDeclaration(fy?: string): Promise<TaxDeclaration> {
  return apiPost<TaxDeclaration>(`/tax/declaration/submit${fy ? `?fy=${fy}` : ""}`, {});
}
export function fetchPendingTaxDeclarations(): Promise<PendingTaxDecl[]> {
  return apiGet<PendingTaxDecl[]>("/tax/declarations/pending");
}
export function decideTaxDeclaration(
  id: string,
  action: "approve" | "reject",
): Promise<TaxDeclaration> {
  return apiPost<TaxDeclaration>(`/tax/declaration/${id}/${action}`, {});
}

// ----------------------------------------------------------------- consent

export interface ConsentLine {
  purpose: string;
  label: string;
  description: string;
  required: boolean;
  version: number;
  status: "granted" | "withdrawn" | "not_given";
  decided_at: string | null;
}

export function fetchConsent(employeeId?: number): Promise<ConsentLine[]> {
  return apiGet<ConsentLine[]>(`/consent${employeeId ? `?employee_id=${employeeId}` : ""}`);
}
export function decideConsent(purpose: string, grant: boolean): Promise<ConsentLine[]> {
  return apiPost<ConsentLine[]>("/consent", { purpose, grant });
}

// ----------------------------------------------------------------- leave

export interface LeaveType {
  id: string;
  key: string;
  code: string;
  label: string;
  color: string;
  description: string | null;
  is_paid: boolean;
  accrual_method: string;
  annual_entitlement: string;
  min_advance_notice_days: number;
  max_consecutive_days: number | null;
  half_day_allowed: boolean;
  requires_doc: boolean;
  show_in_ess: boolean;
}

export interface LeaveBalance {
  leave_type_id: string;
  code: string;
  label: string;
  color: string;
  entitled: string;
  accrued: string;
  carried_forward: string;
  used: string;
  pending: string;
  available: string;
}

export interface LeaveRequest {
  id: string;
  employee_id: number;
  employee_name: string;
  leave_type_id: string;
  leave_code: string;
  leave_label: string;
  color: string;
  start_date: string;
  end_date: string;
  half_day: boolean;
  days: string;
  reason: string | null;
  status: "pending" | "approved" | "rejected" | "cancelled";
  approver_id: number | null;
  approver_name: string | null;
  decision_note: string | null;
  decided_at: string | null;
  can_decide: boolean;
  can_cancel: boolean;
}

export interface LeaveApply {
  leave_type_id: string;
  start_date: string;
  end_date: string;
  half_day?: boolean;
  reason?: string | null;
  employee_id?: number | null;
}

export function fetchLeaveTypes(): Promise<LeaveType[]> {
  return apiGet<LeaveType[]>("/leave/types");
}

export function fetchLeaveBalances(employeeId?: number): Promise<LeaveBalance[]> {
  return apiGet<LeaveBalance[]>(
    `/leave/balances${employeeId ? `?employee_id=${employeeId}` : ""}`,
  );
}

export function fetchLeaveRequests(
  scope: "mine" | "pending" | "all" = "mine",
): Promise<LeaveRequest[]> {
  return apiGet<LeaveRequest[]>(`/leave/requests?scope=${scope}`);
}

export function applyLeave(payload: LeaveApply): Promise<LeaveRequest> {
  return apiPost<LeaveRequest>("/leave/requests", payload);
}

export function decideLeave(
  id: string,
  action: "approve" | "reject" | "cancel",
  note?: string,
): Promise<LeaveRequest> {
  return apiPost<LeaveRequest>(
    `/leave/requests/${id}/${action}`,
    action === "cancel" ? undefined : { note: note ?? null },
  );
}

// ----------------------------------------------------------------- holidays

export interface Holiday {
  id: string;
  name: string;
  holiday_date: string;
  type: "public" | "optional" | "restricted";
}

export function fetchHolidays(year?: number): Promise<Holiday[]> {
  return apiGet<Holiday[]>(`/holidays${year ? `?year=${year}` : ""}`);
}

export function addHoliday(
  name: string,
  holiday_date: string,
  type: Holiday["type"] = "public",
): Promise<Holiday> {
  return apiPost<Holiday>("/holidays", { name, holiday_date, type });
}

// ----------------------------------------------------------------- audit

export interface AuditEvent {
  id: string;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  summary: string | null;
  changes: Record<string, unknown>;
  request_id: string | null;
  created_at: string;
}

export function fetchAuditEvents(params: {
  entity_type?: string;
  limit?: number;
} = {}): Promise<AuditEvent[]> {
  const qs = new URLSearchParams();
  if (params.entity_type) qs.set("entity_type", params.entity_type);
  if (params.limit) qs.set("limit", String(params.limit));
  return apiGet<AuditEvent[]>(`/audit/events${qs.size ? `?${qs}` : ""}`);
}

export async function deleteHoliday(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/holidays/${id}`, {
    method: "DELETE",
    headers: { ...(await authHeader()) },
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Delete failed (${res.status})`);
  }
}
