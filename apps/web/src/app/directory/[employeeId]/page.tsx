"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { fetchEmployee, fetchMe, type EmployeeDetail } from "@/lib/api";
import { Avatar } from "@/components/Avatar";
import { StatusPill } from "@/components/StatusPill";

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">
        {label}
      </div>
      <div className="mt-0.5 text-sm text-ink">{value || "—"}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold text-ink">{title}</h2>
      <div className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">{children}</div>
    </section>
  );
}

export default function ProfilePage({
  params,
}: {
  params: Promise<{ employeeId: string }>;
}) {
  const { employeeId } = use(params);
  const [emp, setEmp] = useState<EmployeeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isHr, setIsHr] = useState(false);

  useEffect(() => {
    fetchEmployee(employeeId)
      .then(setEmp)
      .catch((e: Error) => setError(e.message));
    fetchMe()
      .then((me) => setIsHr(me.is_hr))
      .catch(() => {});
  }, [employeeId]);

  if (error)
    return (
      <div>
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-4 text-sm text-red-strong">
          {error}
        </div>
      </div>
    );
  if (!emp)
    return (
      <div className="text-sm text-mute">
        Loading profile…
      </div>
    );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/directory" className="text-xs text-mute hover:text-ink">
          ← Back to People
        </Link>
        {isHr && (
          <Link
            href={`/directory/${employeeId}/edit`}
            className="rounded-lg border border-line px-3 py-1 text-xs font-medium text-ink hover:bg-line-2"
          >
            ✎ Edit
          </Link>
        )}
      </div>

      {/* Header card */}
      <div className="flex items-center gap-4 rounded-2xl border border-line bg-surface shadow-md">
        <Avatar name={emp.full_name} size={56} />
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-ink">{emp.full_name}</h1>
            <StatusPill status={emp.status} />
          </div>
          <p className="text-sm text-mute">
            {emp.designation ?? "—"} · {emp.department ?? "—"}
          </p>
          <p className="mt-0.5 font-mono text-xs text-mute-2">
            {emp.employee_code} · {emp.email}
          </p>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">
            Tenure
          </div>
          <div className="font-mono text-lg text-ink">{emp.tenure}</div>
        </div>
      </div>

      <Section title="Job">
        <Field label="Designation" value={emp.designation} />
        <Field label="Department" value={emp.department} />
        <Field label="Division" value={emp.division} />
        <Field label="Branch" value={emp.branch} />
        <Field label="Manager" value={emp.manager_name} />
        <Field label="Date of joining" value={emp.date_of_joining} />
        {emp.date_of_leaving && (
          <Field label="Date of leaving" value={emp.date_of_leaving} />
        )}
      </Section>

      <Section title="Contact">
        <Field label="Email" value={emp.email} />
        <Field label="Phone" value={emp.phone} />
        <Field label="Alternate phone" value={emp.alternate_phone} />
      </Section>

      {emp.pii_visible ? (
        <Section title="Personal">
          <Field label="Date of birth" value={emp.date_of_birth} />
          <Field label="Gender" value={emp.gender} />
          <Field label="Marital status" value={emp.marital_status} />
          <Field label="Father's name" value={emp.fathers_name} />
          <Field label="Mother's name" value={emp.mothers_name} />
          <Field label="Spouse" value={emp.spouse_name} />
          <Field label="PAN" value={emp.pan_no} />
          <Field label="Aadhaar" value={emp.aadhaar_no} />
        </Section>
      ) : (
        <div className="rounded-xl border border-line bg-line-2/50 p-4 text-xs text-mute">
          🔒 Personal details are visible to HR and the employee only.
        </div>
      )}
    </div>
  );
}
