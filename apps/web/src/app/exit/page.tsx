"use client";

import { useCallback, useEffect, useState } from "react";
import {
  approveFnf,
  clearItem,
  computeFnf,
  downloadFile,
  fetchEmployeeAssets,
  fetchEmployees,
  fetchExitCases,
  initiateExit,
  payFnf,
  returnAsset,
  type Asset,
  type EmployeeListItem,
  type ExitCase,
} from "@/lib/api";

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

const STATUS_STYLE: Record<string, string> = {
  initiated: "bg-line-2 text-mute",
  clearance: "bg-blue-soft text-blue-strong",
  fnf_computed: "bg-warn-soft text-warn-strong",
  approved: "bg-indigo-soft text-indigo-strong",
  paid: "bg-green-soft text-green-strong",
};

function CaseCard({ c, onChanged, onError }: { c: ExitCase; onChanged: () => void; onError: (m: string) => void }) {
  const [assets, setAssets] = useState<Asset[]>([]);

  const loadAssets = useCallback(() => {
    fetchEmployeeAssets(c.employee_id).then(setAssets).catch(() => {});
  }, [c.employee_id]);
  useEffect(() => loadAssets(), [loadAssets]);

  async function act(fn: () => Promise<unknown>) {
    try {
      await fn();
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function recover(assetId: string) {
    try {
      await returnAsset(assetId);
      loadAssets();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  const allCleared = c.clearance.every((i) => i.status === "cleared");

  return (
    <section className="rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <div>
          <span className="text-sm font-semibold text-ink">{c.employee_name}</span>
          <span className="ml-2 text-[10px] text-mute">
            resigned {c.resignation_date} · LWD {c.last_working_day}
          </span>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLE[c.status]}`}>
          {c.status.replace("_", " ")}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-mute">
            Clearance
          </div>
          <div className="space-y-1.5">
            {c.clearance.map((i) => (
              <div key={i.id} className="flex items-center justify-between text-sm">
                <span className={i.status === "cleared" ? "text-mute line-through" : "text-ink"}>
                  {i.item}
                </span>
                {i.status === "cleared" ? (
                  <span className="text-green-strong">✓</span>
                ) : (
                  <button onClick={() => act(() => clearItem(c.id, i.id))} className="rounded-md border border-line px-2 py-0.5 text-[10px] text-mute hover:text-ink">
                    Clear
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-mute">
            Full &amp; Final
          </div>
          {c.fnf ? (
            <div className="space-y-1 text-sm">
              <Row label="Pending salary" v={c.fnf.pending_salary} />
              <Row label="Gratuity" v={c.fnf.gratuity} />
              <Row label="Leave encashment" v={c.fnf.leave_encashment} />
              <Row label="Notice recovery" v={c.fnf.notice_recovery} neg />
              <Row label="Other recoveries" v={c.fnf.other_recoveries} neg />
              <div className="mt-1 flex justify-between border-t border-line pt-1 font-semibold text-ink">
                <span>Net settlement</span>
                <span>{inr(c.fnf.net_settlement)}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-mute">Not computed yet.</p>
          )}
        </div>
      </div>

      {assets.length > 0 && (
        <div className="border-t border-line px-4 py-3">
          <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-mute">
            Assets to recover
            <span className="rounded-full bg-warn-soft px-1.5 py-0.5 text-[9px] text-warn-strong">
              {assets.length} outstanding
            </span>
          </div>
          <div className="space-y-1.5">
            {assets.map((a) => (
              <div key={a.id} className="flex items-center justify-between text-sm">
                <span className="text-ink">
                  {a.name}
                  <span className="ml-2 font-mono text-[10px] text-mute">{a.asset_tag}</span>
                </span>
                <button
                  onClick={() => recover(a.id)}
                  className="rounded-md border border-line px-2 py-0.5 text-[10px] text-mute hover:text-ink"
                >
                  Mark returned
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap justify-end gap-2 border-t border-line px-4 py-2.5">
        {c.status === "clearance" && (
          <button onClick={() => act(() => computeFnf(c.id))} className="rounded-lg bg-warn-soft px-3 py-1.5 text-xs font-medium text-warn-strong">
            Compute F&amp;F
          </button>
        )}
        {c.status === "fnf_computed" && (
          <button
            onClick={() => act(() => approveFnf(c.id))}
            disabled={!allCleared}
            title={allCleared ? "" : "Clear all items first"}
            className="rounded-lg bg-indigo-soft px-3 py-1.5 text-xs font-medium text-indigo-strong disabled:opacity-50"
          >
            Approve F&amp;F
          </button>
        )}
        {c.status === "approved" && (
          <button onClick={() => act(() => payFnf(c.id))} className="rounded-lg bg-green-soft px-3 py-1.5 text-xs font-medium text-green-strong">
            Pay &amp; revoke access
          </button>
        )}
        {c.status === "paid" && (
          <button
            onClick={() => downloadFile(`/exit/cases/${c.id}/relieving-letter`, `relieving_${c.employee_id}.pdf`)}
            className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-mute hover:text-ink"
          >
            Relieving letter
          </button>
        )}
      </div>
    </section>
  );
}

function Row({ label, v, neg }: { label: string; v: string; neg?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-mute">{label}</span>
      <span className={neg && Number(v) > 0 ? "text-red-strong" : "text-ink"}>
        {neg && Number(v) > 0 ? "−" : ""}
        {inr(v)}
      </span>
    </div>
  );
}

export default function ExitPage() {
  const [cases, setCases] = useState<ExitCase[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchExitCases().then(setCases).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    reload();
    fetchEmployees({ status: "Active" }).then((d) => setEmployees(d.items)).catch(() => {});
  }, [reload]);

  async function initiate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await initiateExit({
        employee_id: Number(fd.get("employee_id")),
        resignation_date: fd.get("resignation_date") as string,
        last_working_day: fd.get("last_working_day") as string,
        reason: (fd.get("reason") as string) || undefined,
        notice_required_days: Number(fd.get("notice")) || 60,
      });
      setShow(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Exit &amp; Full-and-Final</h1>
          <p className="text-xs text-mute">
            Resignation → clearance → F&amp;F → pay → access revoked
          </p>
        </div>
        <button onClick={() => setShow(!show)} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
          + Initiate exit
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {show && (
        <form onSubmit={initiate} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-mute">Employee</label>
            <select name="employee_id" required className="rounded-lg border border-line px-2 py-2 text-sm">
              <option value="">Select…</option>
              {employees.map((m) => (
                <option key={m.employee_id} value={m.employee_id}>{m.full_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-mute">Resignation date</label>
            <input name="resignation_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-mute">Last working day</label>
            <input name="last_working_day" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-mute">Notice (days)</label>
            <input name="notice" type="number" defaultValue={60} className="w-20 rounded-lg border border-line px-2 py-2 text-sm" />
          </div>
          <input name="reason" placeholder="Reason" className="flex-1 min-w-40 rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Initiate</button>
        </form>
      )}

      <div className="space-y-4">
        {cases.map((c) => (
          <CaseCard key={c.id} c={c} onChanged={reload} onError={setError} />
        ))}
        {cases.length === 0 && (
          <div className="rounded-xl border border-line bg-surface p-8 text-center text-sm text-mute shadow-sm">
            No exit cases.
          </div>
        )}
      </div>
    </div>
  );
}
