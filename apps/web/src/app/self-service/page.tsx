"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchAttendance,
  fetchEmployee,
  fetchEmployeePayslips,
  fetchLeaveBalances,
  fetchLeaveRequests,
  fetchMe,
  type AttendanceSummary,
  type EmployeeDetail,
  type LeaveBalance,
  type LeaveRequest,
  type Payslip,
} from "@/lib/api";
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
  }, []);

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
    </div>
  );
}
