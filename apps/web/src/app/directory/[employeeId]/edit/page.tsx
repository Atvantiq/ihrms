"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchDirectoryMeta,
  fetchEmployee,
  fetchEmployees,
  updateEmployee,
  type DirectoryMeta,
  type EmployeeDetail,
  type EmployeeListItem,
  type EmployeeUpdate,
} from "@/lib/api";

function Input({
  label,
  required,
  ...props
}: { label: string; required?: boolean } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
        {label} {required && <span className="text-red">*</span>}
      </label>
      <input
        required={required}
        {...props}
        className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none placeholder:text-mute-2 focus:border-indigo"
      />
    </div>
  );
}

export default function EditEmployeePage({
  params,
}: {
  params: Promise<{ employeeId: string }>;
}) {
  const { employeeId } = use(params);
  const router = useRouter();
  const [emp, setEmp] = useState<EmployeeDetail | null>(null);
  const [meta, setMeta] = useState<DirectoryMeta | null>(null);
  const [managers, setManagers] = useState<EmployeeListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchEmployee(employeeId)
      .then(setEmp)
      .catch((e: Error) => setError(e.message));
    fetchDirectoryMeta()
      .then(setMeta)
      .catch(() => {});
    fetchEmployees({})
      .then((d) =>
        setManagers(d.items.filter((m) => String(m.employee_id) !== employeeId)),
      )
      .catch(() => {});
  }, [employeeId]);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    const val = (k: string) => (fd.get(k) as string)?.trim() || null;
    const payload: EmployeeUpdate = {
      first_name: val("first_name") ?? undefined,
      middle_name: val("middle_name"),
      last_name: val("last_name"),
      phone: val("phone") ?? undefined,
      gender: val("gender"),
      date_of_birth: val("date_of_birth"),
      designation: val("designation") ?? undefined,
      department: val("department") ?? undefined,
      division: val("division") ?? undefined,
      branch: val("branch") ?? undefined,
      circle_id: val("circle_id") ? Number(val("circle_id")) : undefined,
      reporting_manager_id: val("reporting_manager_id")
        ? Number(val("reporting_manager_id"))
        : null,
      date_of_joining: val("date_of_joining") ?? undefined,
      fathers_name: val("fathers_name"),
      mothers_name: val("mothers_name"),
      marital_status: val("marital_status"),
      spouse_name: val("spouse_name"),
      alternate_phone: val("alternate_phone"),
      pan_no: val("pan_no"),
      aadhaar_no: val("aadhaar_no"),
    };
    try {
      await updateEmployee(Number(employeeId), payload);
      router.push(`/directory/${employeeId}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  if (!emp)
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 p-6 text-sm text-mute">
        {error ?? "Loading…"}
      </main>
    );

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 p-6">
      <Link href={`/directory/${employeeId}`} className="text-xs text-mute hover:text-ink">
        ← Back to profile
      </Link>
      <h1 className="mt-2 mb-1 text-xl font-semibold text-ink">
        Edit — {emp.full_name}
      </h1>
      <p className="mb-4 font-mono text-xs text-mute">
        {emp.employee_code} · {emp.email} (email cannot be changed here — it is
        the shared login)
      </p>

      <form onSubmit={submit} className="space-y-4">
        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-ink">Identity</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Input label="First name" name="first_name" required defaultValue={emp.first_name} />
            <Input label="Middle name" name="middle_name" defaultValue={emp.middle_name ?? ""} />
            <Input label="Last name" name="last_name" defaultValue={emp.last_name ?? ""} />
            <Input label="Phone" name="phone" required defaultValue={emp.phone ?? ""} />
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
                Gender
              </label>
              <select
                name="gender"
                defaultValue={emp.gender ?? ""}
                className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm"
              >
                <option value="">—</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </div>
            <Input
              label="Date of birth"
              name="date_of_birth"
              type="date"
              defaultValue={emp.date_of_birth ?? ""}
            />
          </div>
        </section>

        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-ink">Job</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Input label="Designation" name="designation" required list="designations" defaultValue={emp.designation ?? ""} />
            <Input label="Department" name="department" required list="departments" defaultValue={emp.department ?? ""} />
            <Input label="Division" name="division" required list="divisions" defaultValue={emp.division ?? ""} />
            <Input label="Branch" name="branch" required list="branches" defaultValue={emp.branch ?? ""} />
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
                Circle <span className="text-red">*</span>
              </label>
              <select
                name="circle_id"
                required
                defaultValue={emp.circle_id ?? ""}
                className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm"
              >
                {meta?.circle_ids.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
                Reporting manager
              </label>
              <select
                name="reporting_manager_id"
                defaultValue={emp.reporting_manager_id ?? ""}
                className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm"
              >
                <option value="">—</option>
                {managers.map((m) => (
                  <option key={m.employee_id} value={m.employee_id}>
                    {m.full_name} ({m.employee_code})
                  </option>
                ))}
              </select>
            </div>
            <Input
              label="Date of joining"
              name="date_of_joining"
              type="date"
              required
              defaultValue={emp.date_of_joining ?? ""}
            />
          </div>
          <datalist id="designations">
            {meta?.designations.map((d) => <option key={d} value={d} />)}
          </datalist>
          <datalist id="departments">
            {meta?.departments.map((d) => <option key={d} value={d} />)}
          </datalist>
          <datalist id="divisions">
            {meta?.divisions.map((d) => <option key={d} value={d} />)}
          </datalist>
          <datalist id="branches">
            {meta?.branches.map((d) => <option key={d} value={d} />)}
          </datalist>
        </section>

        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-ink">Personal</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Input label="Father's name" name="fathers_name" defaultValue={emp.fathers_name ?? ""} />
            <Input label="Mother's name" name="mothers_name" defaultValue={emp.mothers_name ?? ""} />
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
                Marital status
              </label>
              <select
                name="marital_status"
                defaultValue={emp.marital_status ?? ""}
                className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm"
              >
                <option value="">—</option>
                <option value="single">Single</option>
                <option value="married">Married</option>
                <option value="other">Other</option>
              </select>
            </div>
            <Input label="Spouse" name="spouse_name" defaultValue={emp.spouse_name ?? ""} />
            <Input label="Alternate phone" name="alternate_phone" defaultValue={emp.alternate_phone ?? ""} />
            <Input label="PAN" name="pan_no" defaultValue={emp.pan_no ?? ""} />
            <Input label="Aadhaar" name="aadhaar_no" defaultValue={emp.aadhaar_no ?? ""} />
          </div>
        </section>

        {error && (
          <div className="rounded-lg bg-red-soft px-3 py-2 text-xs text-red-strong">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Link
            href={`/directory/${employeeId}`}
            className="rounded-lg border border-line px-4 py-2 text-sm text-mute hover:text-ink"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface hover:bg-ink-2 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </main>
  );
}
