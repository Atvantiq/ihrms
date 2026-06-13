"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchEmployee,
  fetchEmployeeAssets,
  fetchEmployeePayslips,
  fetchLeaveBalances,
  fetchMe,
  fetchStructure,
  type Asset,
  type EmployeeDetail,
  type LeaveBalance,
  type Payslip,
  type StructureSaved,
} from "@/lib/api";
import { Avatar } from "@/components/Avatar";
import { StatusPill } from "@/components/StatusPill";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

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
  const empIdNum = Number(employeeId);
  const [emp, setEmp] = useState<EmployeeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isHr, setIsHr] = useState(false);
  const [structure, setStructure] = useState<StructureSaved | null>(null);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);

  useEffect(() => {
    fetchEmployee(employeeId)
      .then((e) => {
        setEmp(e);
        // The "360" cross-module sections are sensitive — only load them when
        // the viewer is HR or the employee themselves (same gate as PII).
        if (e.pii_visible) {
          fetchStructure(empIdNum).then(setStructure).catch(() => setStructure(null));
          fetchLeaveBalances(empIdNum).then(setBalances).catch(() => {});
          fetchEmployeePayslips(empIdNum).then(setPayslips).catch(() => {});
          fetchEmployeeAssets(empIdNum).then(setAssets).catch(() => {});
        }
      })
      .catch((e: Error) => setError(e.message));
    fetchMe()
      .then((me) => setIsHr(me.is_hr))
      .catch(() => {});
  }, [employeeId, empIdNum]);

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

      {emp.pii_visible && structure && (
        <Section title="Compensation">
          <Field label="Annual CTC" value={inr(structure.ctc_annual)} />
          <Field label="Monthly gross" value={inr(structure.gross_monthly)} />
          <Field label="Basic" value={inr(structure.basic)} />
          <Field label="HRA" value={inr(structure.hra)} />
          <Field label="Special allowance" value={inr(structure.special_allowance)} />
          <Field label="Tax regime" value={`${structure.tax_regime} regime`} />
        </Section>
      )}

      {emp.pii_visible && balances.length > 0 && (
        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-ink">Leave balances</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {balances.map((b) => (
              <div key={b.leave_type_id} className="rounded-lg border border-line-2 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                    {b.label}
                  </span>
                  <span className="font-mono text-[10px] text-mute-2">{b.code}</span>
                </div>
                <div className="mt-1 text-xl font-semibold text-ink">
                  {Number(b.available)}
                  <span className="text-[10px] font-normal text-mute"> avail</span>
                </div>
                <div className="text-[10px] text-mute-2">
                  {Number(b.used)} used · {Number(b.pending)} pending
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {emp.pii_visible && payslips.length > 0 && (
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <h2 className="border-b border-line px-5 py-3 text-sm font-semibold text-ink">
            Recent payslips
          </h2>
          <div className="divide-y divide-line-2">
            {payslips.slice(0, 6).map((p) => (
              <div
                key={`${p.period_year}-${p.period_month}`}
                className="flex items-center justify-between px-5 py-2.5 text-sm"
              >
                <span className="text-ink">
                  {MONTHS[p.period_month - 1]} {p.period_year}
                </span>
                <span className="flex items-center gap-4">
                  <span className="text-[11px] text-mute">
                    gross {inr(p.gross)} · ded {inr(p.total_deductions)}
                  </span>
                  <span className="font-semibold text-ink">{inr(p.net_pay)}</span>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {emp.pii_visible && assets.length > 0 && (
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <h2 className="border-b border-line px-5 py-3 text-sm font-semibold text-ink">
            Assets held
          </h2>
          <div className="divide-y divide-line-2">
            {assets.map((a) => (
              <div key={a.id} className="flex items-center justify-between px-5 py-2.5 text-sm">
                <span className="text-ink">
                  {a.name}
                  <span className="ml-2 font-mono text-[10px] text-mute">{a.asset_tag}</span>
                </span>
                <span className="text-[11px] capitalize text-mute">{a.category}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
