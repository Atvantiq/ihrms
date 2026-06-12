"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  createEmployee,
  fetchDirectoryMeta,
  fetchEmployees,
  type DirectoryMeta,
  type EmployeeCreate,
  type EmployeeListItem,
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

export default function AddEmployeePage() {
  const router = useRouter();
  const [meta, setMeta] = useState<DirectoryMeta | null>(null);
  const [managers, setManagers] = useState<EmployeeListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchDirectoryMeta()
      .then(setMeta)
      .catch((e: Error) => setError(e.message));
    fetchEmployees({})
      .then((d) => setManagers(d.items))
      .catch(() => {});
  }, []);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    const val = (k: string) => (fd.get(k) as string)?.trim() || null;
    const payload: EmployeeCreate = {
      first_name: val("first_name")!,
      middle_name: val("middle_name"),
      last_name: val("last_name"),
      email: val("email")!,
      phone: val("phone")!,
      employee_code: val("employee_code")!,
      gender: val("gender"),
      date_of_birth: val("date_of_birth"),
      designation: val("designation")!,
      department: val("department")!,
      division: val("division")!,
      branch: val("branch")!,
      circle_id: Number(val("circle_id")),
      reporting_manager_id: val("reporting_manager_id")
        ? Number(val("reporting_manager_id"))
        : null,
      date_of_joining: val("date_of_joining")!,
    };
    try {
      const created = await createEmployee(payload);
      router.push(`/directory/${created.employee_id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 p-6">
      <Link href="/directory" className="text-xs text-mute hover:text-ink">
        ← Back to People
      </Link>
      <h1 className="mt-2 mb-4 text-xl font-semibold text-ink">Add employee</h1>

      <form onSubmit={submit} className="space-y-4">
        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-ink">Identity</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Input label="First name" name="first_name" required placeholder="Priya" />
            <Input label="Middle name" name="middle_name" />
            <Input label="Last name" name="last_name" placeholder="Sharma" />
            <Input label="Email" name="email" type="email" required placeholder="priya@atvantiq.com" />
            <Input label="Phone" name="phone" required placeholder="+91…" />
            <Input label="Employee code" name="employee_code" required placeholder="ATQ/PB/001" />
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
                Gender
              </label>
              <select name="gender" className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm">
                <option value="">—</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </div>
            <Input label="Date of birth" name="date_of_birth" type="date" />
          </div>
        </section>

        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-1 text-sm font-semibold text-ink">Job</h2>
          <p className="mb-4 text-[11px] text-mute-2">
            Pick from existing values where possible — proper masters arrive in a
            later milestone.
          </p>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Input label="Designation" name="designation" required list="designations" />
            <Input label="Department" name="department" required list="departments" />
            <Input label="Division" name="division" required list="divisions" />
            <Input label="Branch" name="branch" required list="branches" />
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
                Circle <span className="text-red">*</span>
              </label>
              <select name="circle_id" required className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm">
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
              <select name="reporting_manager_id" className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm">
                <option value="">—</option>
                {managers.map((m) => (
                  <option key={m.employee_id} value={m.employee_id}>
                    {m.full_name} ({m.employee_code})
                  </option>
                ))}
              </select>
            </div>
            <Input label="Date of joining" name="date_of_joining" type="date" required />
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

        {error && (
          <div className="rounded-lg bg-red-soft px-3 py-2 text-xs text-red-strong">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Link
            href="/directory"
            className="rounded-lg border border-line px-4 py-2 text-sm text-mute hover:text-ink"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface hover:bg-ink-2 disabled:opacity-50"
          >
            {busy ? "Creating…" : "Create employee"}
          </button>
        </div>
      </form>
    </main>
  );
}
