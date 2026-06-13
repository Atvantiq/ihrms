"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  downloadFile,
  fetchConsent,
  fetchEmployee,
  fetchEmployeeAdvances,
  fetchEmployeeAssets,
  fetchEmployeeBand,
  fetchEmployeeHistory,
  fetchEmployeePayslips,
  fetchLeaveBalances,
  fetchLetterTypes,
  fetchMe,
  fetchStatutoryIds,
  fetchStructure,
  setStatutoryIds,
  type Advance,
  type Asset,
  type ConsentLine,
  type EmployeeBand,
  type EmployeeDetail,
  type HistoryEntry,
  type LeaveBalance,
  type LetterType,
  type Payslip,
  type StatutoryIds,
  type StructureSaved,
} from "@/lib/api";

const FIT_STYLE: Record<string, string> = {
  within: "bg-green-soft text-green-strong",
  below: "bg-warn-soft text-warn-strong",
  above: "bg-red-soft text-red-strong",
};

const HISTORY_DOT: Record<HistoryEntry["category"], string> = {
  job: "bg-indigo",
  personal: "bg-blue-strong",
  compensation: "bg-green",
};

function labelField(f: string): string {
  return f.replace(/_/g, " ").replace(/\bid\b/, "").trim();
}

const CONSENT_DOT: Record<ConsentLine["status"], string> = {
  granted: "bg-green",
  withdrawn: "bg-red",
  not_given: "bg-line",
};
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
  const [advances, setAdvances] = useState<Advance[]>([]);
  const [consent, setConsent] = useState<ConsentLine[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [statutory, setStatutory] = useState<StatutoryIds | null>(null);
  const [statMsg, setStatMsg] = useState<string | null>(null);
  const [letterTypes, setLetterTypes] = useState<LetterType[]>([]);
  const [band, setBand] = useState<EmployeeBand | null>(null);

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
          fetchEmployeeAdvances(empIdNum).then(setAdvances).catch(() => {});
          fetchConsent(empIdNum).then(setConsent).catch(() => {});
          fetchEmployeeHistory(empIdNum).then(setHistory).catch(() => {});
          fetchStatutoryIds(empIdNum).then(setStatutory).catch(() => {});
          fetchEmployeeBand(empIdNum).then(setBand).catch(() => {});
        }
      })
      .catch((e: Error) => setError(e.message));
    fetchMe()
      .then((me) => {
        setIsHr(me.is_hr);
        if (me.is_hr) fetchLetterTypes().then(setLetterTypes).catch(() => {});
      })
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
          {band?.band_code && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                Band
              </div>
              <div className="mt-0.5 flex items-center gap-2 text-sm text-ink">
                {band.band_code} · {band.band_name}
                {band.fit && (
                  <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase ${FIT_STYLE[band.fit]}`}>
                    {band.fit} band
                  </span>
                )}
              </div>
            </div>
          )}
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

      {emp.pii_visible && advances.some((a) => a.status === "active") && (
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <h2 className="border-b border-line px-5 py-3 text-sm font-semibold text-ink">
            Advances &amp; loans
          </h2>
          <div className="divide-y divide-line-2">
            {advances
              .filter((a) => a.status === "active")
              .map((a) => (
                <div key={a.id} className="flex items-center justify-between px-5 py-2.5 text-sm">
                  <span className="text-ink capitalize">
                    {a.kind}
                    {a.reason && <span className="ml-2 text-[11px] text-mute">{a.reason}</span>}
                  </span>
                  <span className="text-[11px] text-mute">
                    EMI {inr(a.emi_amount)} · outstanding{" "}
                    <span className="font-semibold text-warn">{inr(a.outstanding)}</span>
                  </span>
                </div>
              ))}
          </div>
        </section>
      )}

      {emp.pii_visible && consent.length > 0 && (
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <h2 className="border-b border-line px-5 py-3 text-sm font-semibold text-ink">
            Data &amp; privacy consent
          </h2>
          <div className="divide-y divide-line-2">
            {consent.map((c) => (
              <div key={c.purpose} className="flex items-center justify-between px-5 py-2.5 text-sm">
                <span className="flex items-center gap-2 text-ink">
                  <span className={`h-2 w-2 rounded-full ${CONSENT_DOT[c.status]}`} />
                  {c.label}
                </span>
                <span className="text-[11px] capitalize text-mute">
                  {c.status.replace("_", " ")}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {isHr && letterTypes.length > 0 && (
        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-1 text-sm font-semibold text-ink">Letters</h2>
          <p className="mb-3 text-[11px] text-mute">
            Generate a signed-on-behalf HR letter as a PDF.
          </p>
          <div className="flex flex-wrap gap-2">
            {letterTypes.map((lt) => (
              <button
                key={lt.key}
                onClick={() =>
                  downloadFile(`/letters/${lt.key}/${empIdNum}`, `${lt.key}_${empIdNum}.pdf`)
                }
                className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-line-2"
              >
                {lt.label}
              </button>
            ))}
          </div>
        </section>
      )}

      {emp.pii_visible && statutory && (
        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-1 text-sm font-semibold text-ink">Statutory IDs</h2>
          <p className="mb-4 text-[11px] text-mute">
            UAN, ESIC &amp; PF — used to generate the PF ECR / ESI / PT return files.
          </p>
          {statMsg && <div className="mb-3 text-xs text-green-strong">{statMsg}</div>}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              try {
                const saved = await setStatutoryIds(empIdNum, {
                  uan: (fd.get("uan") as string) || null,
                  esic_ip: (fd.get("esic_ip") as string) || null,
                  pf_number: (fd.get("pf_number") as string) || null,
                  pt_state: (fd.get("pt_state") as string) || "KA",
                });
                setStatutory(saved);
                setStatMsg("Saved");
                setTimeout(() => setStatMsg(null), 2500);
              } catch (err) {
                setError((err as Error).message);
              }
            }}
            className="grid grid-cols-2 gap-3 sm:grid-cols-4"
          >
            <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
              UAN
              <input name="uan" defaultValue={statutory.uan ?? ""} disabled={!isHr} placeholder="12 digits" className="mt-1 w-full rounded-lg border border-line px-2 py-1.5 text-sm font-normal normal-case text-ink disabled:bg-line-2/40" />
            </label>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
              ESIC IP
              <input name="esic_ip" defaultValue={statutory.esic_ip ?? ""} disabled={!isHr} className="mt-1 w-full rounded-lg border border-line px-2 py-1.5 text-sm font-normal normal-case text-ink disabled:bg-line-2/40" />
            </label>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
              PF number
              <input name="pf_number" defaultValue={statutory.pf_number ?? ""} disabled={!isHr} className="mt-1 w-full rounded-lg border border-line px-2 py-1.5 text-sm font-normal normal-case text-ink disabled:bg-line-2/40" />
            </label>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
              PT state
              <input name="pt_state" defaultValue={statutory.pt_state} disabled={!isHr} maxLength={2} className="mt-1 w-full rounded-lg border border-line px-2 py-1.5 text-sm font-normal uppercase text-ink disabled:bg-line-2/40" />
            </label>
            {isHr && (
              <div className="col-span-2 sm:col-span-4">
                <button className="rounded-lg bg-ink px-4 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
                  Save IDs
                </button>
              </div>
            )}
          </form>
        </section>
      )}

      {emp.pii_visible && history.length > 0 && (
        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-ink">Change history</h2>
          <ol className="space-y-3">
            {history.map((h, i) => (
              <li key={i} className="flex gap-3">
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${HISTORY_DOT[h.category]}`} />
                <div className="flex-1 text-sm">
                  <div className="text-ink">
                    <span className="capitalize">{labelField(h.field)}</span>
                    {h.old_value && (
                      <span className="text-mute"> · {h.old_value} →</span>
                    )}{" "}
                    <span className="font-medium">{h.new_value ?? "—"}</span>
                  </div>
                  <div className="text-[10px] text-mute-2">
                    {h.effective_date} · {h.category}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
