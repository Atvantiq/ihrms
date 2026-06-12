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

export function fetchEmployees(params: {
  q?: string;
  department?: string;
  status?: string;
}): Promise<EmployeeListOut> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.department) qs.set("department", params.department);
  if (params.status) qs.set("status", params.status);
  const suffix = qs.size ? `?${qs}` : "";
  return apiGet<EmployeeListOut>(`/employees${suffix}`);
}

export function fetchEmployee(employeeId: string): Promise<EmployeeDetail> {
  return apiGet<EmployeeDetail>(`/employees/${employeeId}`);
}
