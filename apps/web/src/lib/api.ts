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

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json", ...(await authHeader()) },
    cache: "no-store",
  });
  if (res.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
    throw new Error("Not signed in");
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
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
  if (!res.ok) {
    let detail = await res.text();
    try {
      detail = JSON.parse(detail).detail ?? detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
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
  if (!res.ok) {
    let detail = await res.text();
    try {
      detail = JSON.parse(detail).detail ?? detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
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
  if (!res.ok) {
    let detail = await res.text();
    try {
      detail = JSON.parse(detail).detail ?? detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
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

export function fetchEmployee(employeeId: string): Promise<EmployeeDetail> {
  return apiGet<EmployeeDetail>(`/employees/${employeeId}`);
}

// ----------------------------------------------------------------- payroll

export interface StructurePreview {
  ctc_annual: string;
  basic: string;
  hra: string;
  special_allowance: string;
  gross_monthly: string;
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

export async function setStructure(
  employeeId: number,
  ctcAnnual: number,
  effectiveFrom: string,
): Promise<StructurePreview & { employee_id: number }> {
  return apiPut(`/payroll/structures/${employeeId}`, {
    ctc_annual: ctcAnnual,
    effective_from: effectiveFrom,
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
  if (!res.ok) {
    let detail = await res.text();
    try {
      detail = JSON.parse(detail).detail ?? detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
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
