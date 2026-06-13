"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  decideConsent,
  fetchAttendance,
  fetchClaimCategories,
  fetchClaims,
  fetchConsent,
  fetchEmployee,
  fetchEmployeePayslips,
  fetchLeaveBalances,
  fetchLeaveRequests,
  fetchMe,
  fetchMyCheckIns,
  fileClaim,
  logCheckIn,
  raiseAssetRequest,
  type AttendanceSummary,
  type CheckIn,
  type Claim,
  type ConsentLine,
  type EmployeeDetail,
  type LeaveBalance,
  type LeaveRequest,
  type Payslip,
} from "@/lib/api";

const CLAIM_STATUS_STYLE: Record<Claim["status"], string> = {
  pending: "bg-warn-soft text-warn-strong",
  approved: "bg-blue-soft text-blue-strong",
  rejected: "bg-red-soft text-red-strong",
  paid: "bg-green-soft text-green-strong",
};

const CONSENT_STATUS_STYLE: Record<ConsentLine["status"], string> = {
  granted: "bg-green-soft text-green-strong",
  withdrawn: "bg-red-soft text-red-strong",
  not_given: "bg-line-2 text-mute",
};
import { Avatar } from "@/components/Avatar";
import { StatusPill } from "@/components/StatusPill";
import { LeaveStatusBadge } from "@/components/LeaveStatusBadge";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">{label}</div>
      <div className="text-2xl font-semibold text-ink">{value}</div>
      <div className="text-[10px] text-mute-2">{hint}</div>
    </div>
  );
}

function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export default function SelfServicePage() {
  const [emp, setEmp] = useState<EmployeeDetail | null>(null);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [attendance, setAttendance] = useState<AttendanceSummary | null>(null);
  const [consent, setConsent] = useState<ConsentLine[]>([]);
  const [checkIns, setCheckIns] = useState<CheckIn[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [claimCats, setClaimCats] = useState<string[]>([]);
  const [assetMsg, setAssetMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe()
      .then((me) => {
        const id = me.employee_id;
        const now = new Date();
        fetchEmployee(String(id)).then(setEmp).catch(() => {});
        fetchLeaveBalances().then(setBalances).catch(() => {});
        fetchEmployeePayslips(id).then(setPayslips).catch(() => {});
        fetchLeaveRequests("mine").then(setRequests).catch(() => {});
        fetchAttendance(now.getFullYear(), now.getMonth() + 1, id)
          .then(setAttendance)
          .catch(() => {});
      })
      .catch((e: Error) => setError(e.message));
    fetchConsent().then(setConsent).catch(() => {});
    fetchMyCheckIns().then(setCheckIns).catch(() => {});
    fetchClaims("mine").then(setClaims).catch(() => {});
    fetchClaimCategories().then(setClaimCats).catch(() => {});
  }, []);

  async function submitClaim(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await fileClaim({
        category: fd.get("category") as string,
        description: fd.get("description") as string,
        claim_date: fd.get("claim_date") as string,
        amount: fd.get("amount") as string,
      });
      form.reset();
      fetchClaims("mine").then(setClaims).catch(() => {});
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function toggleConsent(purpose: string, grant: boolean) {
    try {
      setConsent(await decideConsent(purpose, grant));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function submitAssetRequest(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await raiseAssetRequest(fd.get("category") as string, fd.get("justification") as string);
      form.reset();
      setAssetMsg("Request submitted to HR.");
      setTimeout(() => setAssetMsg(null), 3000);
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function submitCheckIn(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await logCheckIn({
        highlights: fd.get("highlights") as string,
        challenges: (fd.get("challenges") as string) || null,
        mood: Number(fd.get("mood")),
      });
      form.reset();
      fetchMyCheckIns().then(setCheckIns).catch(() => {});
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const leaveAvailable = balances.reduce((s, b) => s + Number(b.available), 0);
  const latestNet = payslips[0]?.net_pay;

  return (
    <div className="space-y-5">
      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}
        </div>
      )}

      {/* Greeting header */}
      <div className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-5 shadow-md">
        {emp && <Avatar name={emp.full_name} size={48} />}
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-ink">
              {emp ? emp.full_name : "Self-service"}
            </h1>
            {emp && <StatusPill status={emp.status} />}
          </div>
          <p className="text-sm text-mute">
            {emp ? `${emp.designation ?? "—"} · ${emp.department ?? "—"}` : "Your workspace"}
          </p>
        </div>
        {emp && (
          <Link
            href={`/directory/${emp.employee_id}`}
            className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-line-2"
          >
            View full profile →
          </Link>
        )}
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Leave available" value={String(leaveAvailable)} hint="across all types" />
        <Stat
          label="Attendance"
          value={attendance ? `${attendance.present + attendance.wfh}/${attendance.payable || "—"}` : "—"}
          hint="present this month"
        />
        <Stat label="Latest net pay" value={latestNet ? inr(latestNet) : "—"} hint="last payslip" />
        <Stat label="My requests" value={String(requests.length)} hint="leave applications" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel
          title="My leave balances"
          action={
            <Link href="/leave" className="text-xs text-indigo-strong hover:underline">
              Apply →
            </Link>
          }
        >
          {balances.length > 0 ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {balances.map((b) => (
                <div key={b.leave_type_id} className="rounded-lg border border-line-2 p-3">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                    {b.label}
                  </div>
                  <div className="mt-0.5 text-xl font-semibold text-ink">
                    {Number(b.available)}
                  </div>
                  <div className="text-[10px] text-mute-2">
                    {Number(b.used)} used · {Number(b.pending)} pending
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-mute">No leave balances yet.</p>
          )}
        </Panel>

        <Panel
          title="Recent payslips"
          action={
            <Link href="/payroll" className="text-xs text-indigo-strong hover:underline">
              Payroll →
            </Link>
          }
        >
          {payslips.length > 0 ? (
            <ul className="space-y-2">
              {payslips.slice(0, 5).map((p) => (
                <li
                  key={`${p.period_year}-${p.period_month}`}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-ink">
                    {MONTHS[p.period_month - 1]} {p.period_year}
                  </span>
                  <span className="font-semibold text-ink">{inr(p.net_pay)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-mute">No payslips yet.</p>
          )}
        </Panel>

        <Panel
          title="My leave requests"
          action={
            <Link href="/leave" className="text-xs text-indigo-strong hover:underline">
              All →
            </Link>
          }
        >
          {requests.length > 0 ? (
            <ul className="space-y-2">
              {requests.slice(0, 5).map((r) => (
                <li key={r.id} className="flex items-center justify-between text-sm">
                  <span className="flex-1 text-ink">
                    {r.start_date} → {r.end_date}
                    <span className="ml-2 text-[11px] text-mute">{Number(r.days)}d</span>
                  </span>
                  <LeaveStatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-mute">No leave requests yet.</p>
          )}
        </Panel>

        <Panel title="Quick actions">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <Link href="/leave" className="rounded-lg border border-line px-3 py-2 text-center text-ink hover:bg-line-2">
              Apply for leave
            </Link>
            <Link href="/timesheet" className="rounded-lg border border-line px-3 py-2 text-center text-ink hover:bg-line-2">
              Fill timesheet
            </Link>
            <Link href="/attendance" className="rounded-lg border border-line px-3 py-2 text-center text-ink hover:bg-line-2">
              My attendance
            </Link>
            <Link href="/tasks" className="rounded-lg border border-line px-3 py-2 text-center text-ink hover:bg-line-2">
              My tasks
            </Link>
          </div>
        </Panel>
      </div>

      <section className="rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5">
          <h2 className="text-sm font-semibold text-ink">Check-in</h2>
          <p className="text-[11px] text-mute">A quick note for your manager — what went well, what&apos;s hard, how you feel.</p>
        </div>
        <form onSubmit={submitCheckIn} className="flex flex-wrap items-end gap-3 border-b border-line-2 p-4">
          <input name="highlights" required maxLength={1000} placeholder="Highlights" className="min-w-44 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="challenges" maxLength={1000} placeholder="Challenges (optional)" className="min-w-44 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <select name="mood" defaultValue="4" className="rounded-lg border border-line px-2 py-2 text-sm">
            <option value="1">😟 Struggling</option>
            <option value="2">🙁 Low</option>
            <option value="3">😐 Okay</option>
            <option value="4">🙂 Good</option>
            <option value="5">😄 Great</option>
          </select>
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Check in</button>
        </form>
        <div className="divide-y divide-line-2">
          {checkIns.length === 0 && <p className="px-4 py-3 text-sm text-mute">No check-ins yet.</p>}
          {checkIns.slice(0, 5).map((c) => (
            <div key={c.id} className="px-4 py-2.5 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-ink">{c.highlights}</span>
                <span className="ml-2 text-[11px] capitalize text-mute">{c.mood_label} · {c.check_in_date}</span>
              </div>
              {c.challenges && <div className="text-[11px] text-mute">⚠ {c.challenges}</div>}
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5">
          <h2 className="text-sm font-semibold text-ink">Request an asset</h2>
          <p className="text-[11px] text-mute">Ask HR for equipment — they&apos;ll review and allocate from stock.</p>
        </div>
        {assetMsg && (
          <div className="border-b border-line-2 bg-green-soft/40 px-4 py-2 text-xs text-green-strong">
            {assetMsg}
          </div>
        )}
        <form onSubmit={submitAssetRequest} className="flex flex-wrap items-end gap-3 p-4">
          <select name="category" defaultValue="laptop" className="rounded-lg border border-line px-2 py-2 text-sm capitalize">
            {["laptop", "desktop", "phone", "monitor", "peripheral", "furniture", "other"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <input name="justification" required maxLength={500} placeholder="Why do you need it?" className="min-w-44 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Request</button>
        </form>
      </section>

      <section className="rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5">
          <h2 className="text-sm font-semibold text-ink">Expense claims</h2>
          <p className="text-[11px] text-mute">File a reimbursement — approved claims are added to your next payout.</p>
        </div>
        <form onSubmit={submitClaim} className="flex flex-wrap items-end gap-3 border-b border-line-2 p-4">
          <select name="category" className="rounded-lg border border-line px-2 py-2 text-sm capitalize">
            {claimCats.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <input name="claim_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
          <input name="amount" type="number" min="1" step="1" required placeholder="Amount ₹" className="w-28 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="description" required maxLength={300} placeholder="Description" className="min-w-44 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">File claim</button>
        </form>
        <div className="divide-y divide-line-2">
          {claims.length === 0 && <p className="px-4 py-3 text-sm text-mute">No claims filed.</p>}
          {claims.map((c) => (
            <div key={c.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <span className="text-ink">
                <span className="font-mono text-[11px]">₹{Number(c.amount).toLocaleString("en-IN")}</span>
                <span className="ml-2 text-[11px] capitalize text-mute">{c.category} · {c.claim_date} · {c.description}</span>
              </span>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${CLAIM_STATUS_STYLE[c.status]}`}>
                {c.status}
              </span>
            </div>
          ))}
        </div>
      </section>

      {consent.length > 0 && (
        <section className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5">
            <h2 className="text-sm font-semibold text-ink">Data &amp; privacy consent</h2>
            <p className="text-[11px] text-mute">
              Manage how Atvantiq processes your personal data (DPDP Act). You can
              withdraw consent at any time.
            </p>
          </div>
          <div className="divide-y divide-line-2">
            {consent.map((c) => (
              <div key={c.purpose} className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-ink">{c.label}</span>
                    {c.required && (
                      <span className="rounded-full bg-warn-soft px-1.5 py-0.5 text-[9px] font-semibold uppercase text-warn-strong">
                        needed for employment
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-mute">{c.description}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${CONSENT_STATUS_STYLE[c.status]}`}>
                    {c.status.replace("_", " ")}
                  </span>
                  {c.status === "granted" ? (
                    <button
                      onClick={() => toggleConsent(c.purpose, false)}
                      className="rounded-md border border-line px-2 py-1 text-[11px] font-medium text-mute hover:text-red-strong"
                    >
                      Withdraw
                    </button>
                  ) : (
                    <button
                      onClick={() => toggleConsent(c.purpose, true)}
                      className="rounded-md bg-ink px-3 py-1 text-[11px] font-medium text-surface hover:bg-ink-2"
                    >
                      Grant
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
