"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  applyLeave,
  decideLeave,
  fetchLeaveBalances,
  fetchLeaveRequests,
  fetchLeaveTypes,
  type LeaveBalance,
  type LeaveRequest,
  type LeaveType,
} from "@/lib/api";
import { LeaveStatusBadge } from "@/components/LeaveStatusBadge";

function BalanceCard({ b }: { b: LeaveBalance }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-mute">
          {b.label}
        </span>
        <span className="font-mono text-[10px] text-mute-2">{b.code}</span>
      </div>
      <div className="mt-1 text-2xl font-semibold text-ink">
        {Number(b.available)}
        <span className="text-xs font-normal text-mute"> available</span>
      </div>
      <div className="mt-2 flex gap-3 text-[10px] text-mute">
        <span>Accrued {Number(b.accrued)}</span>
        <span>Used {Number(b.used)}</span>
        {Number(b.pending) > 0 && (
          <span className="text-warn-strong">Pending {Number(b.pending)}</span>
        )}
      </div>
    </div>
  );
}

function ApplyForm({
  types,
  onApplied,
  onClose,
}: {
  types: LeaveType[];
  onApplied: () => void;
  onClose: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    try {
      await applyLeave({
        leave_type_id: fd.get("leave_type_id") as string,
        start_date: fd.get("start_date") as string,
        end_date: fd.get("end_date") as string,
        half_day: fd.get("half_day") === "on",
        reason: (fd.get("reason") as string)?.trim() || null,
      });
      onApplied();
      onClose();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-xl border border-line bg-surface p-5 shadow-sm"
    >
      <h2 className="mb-4 text-sm font-semibold text-ink">Apply for leave</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="col-span-2 sm:col-span-1">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
            Leave type
          </label>
          <select
            name="leave_type_id"
            required
            className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm"
          >
            {types.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label} ({t.code})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
            From
          </label>
          <input
            type="date"
            name="start_date"
            required
            className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
            To
          </label>
          <input
            type="date"
            name="end_date"
            required
            className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm"
          />
        </div>
        <label className="flex items-end gap-1.5 pb-2 text-xs text-mute">
          <input type="checkbox" name="half_day" /> Half day
        </label>
      </div>
      <div className="mt-4">
        <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
          Reason
        </label>
        <input
          name="reason"
          placeholder="Optional note for your manager"
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none placeholder:text-mute-2 focus:border-indigo"
        />
      </div>
      {error && (
        <div className="mt-3 rounded-lg bg-red-soft px-3 py-2 text-xs text-red-strong">
          {error}
        </div>
      )}
      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-line px-4 py-2 text-sm text-mute hover:text-ink"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface hover:bg-ink-2 disabled:opacity-50"
        >
          {busy ? "Submitting…" : "Submit request"}
        </button>
      </div>
    </form>
  );
}

function RequestRow({
  r,
  showEmployee,
  onAction,
}: {
  r: LeaveRequest;
  showEmployee: boolean;
  onAction: (id: string, action: "approve" | "reject" | "cancel") => void;
}) {
  return (
    <tr className="border-b border-line-2 last:border-0">
      {showEmployee && (
        <td className="px-4 py-2 font-medium text-ink">{r.employee_name}</td>
      )}
      <td className="px-3 py-2">
        <span className="rounded-md bg-line-2 px-1.5 py-0.5 font-mono text-[10px] text-mute">
          {r.leave_code}
        </span>
      </td>
      <td className="px-3 py-2 text-mute">
        {r.start_date}
        {r.end_date !== r.start_date && ` → ${r.end_date}`}
        {r.half_day && " (½)"}
      </td>
      <td className="px-3 py-2 font-mono text-xs text-ink">{Number(r.days)}</td>
      <td className="px-3 py-2 text-mute">{r.reason ?? "—"}</td>
      <td className="px-3 py-2">
        <LeaveStatusBadge status={r.status} />
        {r.decision_note && (
          <div className="mt-0.5 text-[10px] text-mute-2">“{r.decision_note}”</div>
        )}
      </td>
      <td className="px-3 py-2 text-right">
        <div className="flex justify-end gap-1.5">
          {r.can_decide && (
            <>
              <button
                onClick={() => onAction(r.id, "approve")}
                className="rounded-md bg-green-soft px-2 py-1 text-[11px] font-medium text-green-strong hover:opacity-80"
              >
                Approve
              </button>
              <button
                onClick={() => onAction(r.id, "reject")}
                className="rounded-md bg-red-soft px-2 py-1 text-[11px] font-medium text-red-strong hover:opacity-80"
              >
                Reject
              </button>
            </>
          )}
          {r.can_cancel && !r.can_decide && (
            <button
              onClick={() => onAction(r.id, "cancel")}
              className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-ink"
            >
              Cancel
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

function RequestTable({
  title,
  requests,
  showEmployee,
  onAction,
  empty,
}: {
  title: string;
  requests: LeaveRequest[];
  showEmployee: boolean;
  onAction: (id: string, action: "approve" | "reject" | "cancel") => void;
  empty: string;
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
        {title} <span className="font-normal text-mute">({requests.length})</span>
      </div>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
            {showEmployee && <th className="px-4 py-2 font-semibold">Employee</th>}
            <th className="px-3 py-2 font-semibold">Type</th>
            <th className="px-3 py-2 font-semibold">Dates</th>
            <th className="px-3 py-2 font-semibold">Days</th>
            <th className="px-3 py-2 font-semibold">Reason</th>
            <th className="px-3 py-2 font-semibold">Status</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {requests.map((r) => (
            <RequestRow
              key={r.id}
              r={r}
              showEmployee={showEmployee}
              onAction={onAction}
            />
          ))}
          {requests.length === 0 && (
            <tr>
              <td
                colSpan={showEmployee ? 7 : 6}
                className="px-4 py-8 text-center text-mute"
              >
                {empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

export default function LeavePage() {
  const [types, setTypes] = useState<LeaveType[]>([]);
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [mine, setMine] = useState<LeaveRequest[]>([]);
  const [approvals, setApprovals] = useState<LeaveRequest[]>([]);
  const [showApply, setShowApply] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchLeaveBalances().then(setBalances).catch((e) => setError(e.message));
    fetchLeaveRequests("mine").then(setMine).catch(() => {});
    fetchLeaveRequests("pending").then(setApprovals).catch(() => setApprovals([]));
  }, []);

  useEffect(() => {
    fetchLeaveTypes().then(setTypes).catch((e) => setError(e.message));
    reload();
  }, [reload]);

  async function onAction(
    id: string,
    action: "approve" | "reject" | "cancel",
  ) {
    let note: string | undefined;
    if (action === "reject") {
      note = window.prompt("Reason for rejection (optional):") ?? undefined;
    }
    try {
      await decideLeave(id, action, note);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <Link href="/directory" className="text-xs text-mute hover:text-ink">
            ← People
          </Link>
          <h1 className="mt-1 text-xl font-semibold text-ink">Leave</h1>
          <p className="text-xs text-mute">
            Your balances and requests · approvals for your team
          </p>
        </div>
        {!showApply && (
          <button
            onClick={() => setShowApply(true)}
            className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2"
          >
            + Apply for leave
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}{" "}
          <button onClick={() => setError(null)} className="underline">
            dismiss
          </button>
        </div>
      )}

      {showApply && (
        <ApplyForm
          types={types}
          onApplied={reload}
          onClose={() => setShowApply(false)}
        />
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {balances.map((b) => (
          <BalanceCard key={b.leave_type_id} b={b} />
        ))}
      </div>

      {approvals.length > 0 && (
        <RequestTable
          title="Pending approvals"
          requests={approvals}
          showEmployee
          onAction={onAction}
          empty="Nothing awaiting your approval."
        />
      )}

      <RequestTable
        title="My requests"
        requests={mine}
        showEmployee={false}
        onAction={onAction}
        empty="You haven't applied for any leave yet."
      />
    </div>
  );
}
