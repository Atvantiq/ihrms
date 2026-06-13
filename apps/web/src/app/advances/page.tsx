"use client";

import { useCallback, useEffect, useState } from "react";
import {
  cancelAdvance,
  fetchAdvances,
  fetchEmployees,
  issueAdvance,
  type Advance,
  type EmployeeListItem,
} from "@/lib/api";

const STATUS_STYLE: Record<Advance["status"], string> = {
  active: "bg-blue-soft text-blue-strong",
  closed: "bg-green-soft text-green-strong",
  cancelled: "bg-line-2 text-mute",
};

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

export default function AdvancesPage() {
  const [advances, setAdvances] = useState<Advance[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const reload = useCallback(() => {
    fetchAdvances().then(setAdvances).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    reload();
    fetchEmployees({ limit: 500 }).then((r) => setEmployees(r.items)).catch(() => {});
  }, [reload]);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await issueAdvance({
        employee_id: Number(fd.get("employee_id")),
        kind: fd.get("kind") as string,
        principal_amount: fd.get("principal_amount") as string,
        emi_amount: fd.get("emi_amount") as string,
        reason: (fd.get("reason") as string) || null,
      });
      form.reset();
      setShowAdd(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function cancel(id: string) {
    try {
      await cancelAdvance(id);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const active = advances.filter((a) => a.status === "active");
  const totalOutstanding = active.reduce((s, a) => s + Number(a.outstanding), 0);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Advances &amp; Loans</h1>
          <p className="text-xs text-mute">
            Salary advances · loans · auto-recovered as EMIs in payroll, settled at exit
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2"
        >
          + Issue advance
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">Active</div>
          <div className="text-2xl font-semibold text-ink">{active.length}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">Outstanding</div>
          <div className="text-2xl font-semibold text-warn">{inr(totalOutstanding)}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">Total issued</div>
          <div className="text-2xl font-semibold text-ink">{advances.length}</div>
        </div>
      </div>

      {showAdd && (
        <form onSubmit={add} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <select name="employee_id" required className="min-w-44 rounded-lg border border-line px-2 py-2 text-sm">
            <option value="">Employee…</option>
            {employees.map((e) => <option key={e.employee_id} value={e.employee_id}>{e.full_name}</option>)}
          </select>
          <select name="kind" className="rounded-lg border border-line px-2 py-2 text-sm">
            <option value="advance">Advance</option>
            <option value="loan">Loan</option>
          </select>
          <input name="principal_amount" type="number" min="1" step="1" required placeholder="Principal ₹" className="w-32 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="emi_amount" type="number" min="1" step="1" required placeholder="EMI ₹/mo" className="w-28 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="reason" placeholder="Reason" className="min-w-36 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Issue</button>
        </form>
      )}

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">Employee</th>
              <th className="px-3 py-2 font-semibold">Type</th>
              <th className="px-3 py-2 font-semibold">Principal</th>
              <th className="px-3 py-2 font-semibold">EMI</th>
              <th className="px-3 py-2 font-semibold">Recovered</th>
              <th className="px-3 py-2 font-semibold">Outstanding</th>
              <th className="px-3 py-2 font-semibold">Status</th>
              <th className="px-3 py-2 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {advances.map((a) => (
              <tr key={a.id} className="border-b border-line-2 last:border-0">
                <td className="px-4 py-2">
                  <span className="font-medium text-ink">{a.employee_name ?? a.employee_id}</span>
                  {a.reason && <span className="block text-[10px] text-mute">{a.reason}</span>}
                </td>
                <td className="px-3 py-2 capitalize text-mute">{a.kind}</td>
                <td className="px-3 py-2 text-ink">{inr(a.principal_amount)}</td>
                <td className="px-3 py-2 text-mute">{inr(a.emi_amount)}</td>
                <td className="px-3 py-2 text-green">{inr(a.recovered)}</td>
                <td className="px-3 py-2 font-semibold text-ink">{inr(a.outstanding)}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLE[a.status]}`}>
                    {a.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  {a.status === "active" && (
                    <button
                      onClick={() => cancel(a.id)}
                      className="rounded-md border border-line px-2 py-1 text-[11px] font-medium text-mute hover:text-red-strong"
                    >
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {advances.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-mute">
                  No advances issued yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
