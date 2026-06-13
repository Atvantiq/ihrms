"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addPipCheckpoint,
  closePip,
  fetchEmployees,
  fetchMe,
  fetchPips,
  openPip,
  type EmployeeListItem,
  type Pip,
} from "@/lib/api";

const STATUS_STYLE: Record<Pip["status"], string> = {
  active: "bg-warn-soft text-warn-strong",
  improved: "bg-green-soft text-green-strong",
  extended: "bg-blue-soft text-blue-strong",
  terminated: "bg-red-soft text-red-strong",
  closed: "bg-line-2 text-mute",
};

const RATING_STYLE: Record<string, string> = {
  on_track: "text-green",
  at_risk: "text-warn",
  off_track: "text-red-strong",
};

export default function PipPage() {
  const [pips, setPips] = useState<Pip[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [isHr, setIsHr] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const reload = useCallback((hr: boolean) => {
    fetchPips(hr ? "managed" : "mine").then(setPips).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    fetchMe().then((me) => {
      setIsHr(me.is_hr);
      reload(me.is_hr);
      if (me.is_hr) fetchEmployees({ limit: 500 }).then((r) => setEmployees(r.items)).catch(() => {});
    });
  }, [reload]);

  async function open(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await openPip({
        employee_id: Number(fd.get("employee_id")),
        reason: fd.get("reason") as string,
        objectives: fd.get("objectives") as string,
        start_date: fd.get("start_date") as string,
        end_date: fd.get("end_date") as string,
      });
      form.reset();
      setShowAdd(false);
      reload(isHr);
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function checkpoint(id: string) {
    const rating = prompt("Rating? on_track / at_risk / off_track", "on_track");
    if (!rating) return;
    try {
      await addPipCheckpoint(id, rating, prompt("Note (optional)") || undefined);
      reload(isHr);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function close(id: string) {
    const outcome = prompt("Outcome? improved / extended / terminated / closed", "improved");
    if (!outcome) return;
    try {
      await closePip(id, outcome);
      reload(isHr);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Performance improvement plans</h1>
          <p className="text-xs text-mute">Structured objectives, checkpoints and outcomes</p>
        </div>
        {isHr && (
          <button onClick={() => setShowAdd(!showAdd)} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
            + Open PIP
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {showAdd && (
        <form onSubmit={open} className="space-y-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="flex flex-wrap gap-3">
            <select name="employee_id" required className="min-w-44 rounded-lg border border-line px-2 py-2 text-sm">
              <option value="">Employee…</option>
              {employees.map((e) => <option key={e.employee_id} value={e.employee_id}>{e.full_name}</option>)}
            </select>
            <input name="start_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
            <input name="end_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
          </div>
          <input name="reason" required maxLength={500} placeholder="Reason" className="w-full rounded-lg border border-line px-3 py-2 text-sm" />
          <textarea name="objectives" required maxLength={2000} rows={2} placeholder="Objectives & success criteria" className="w-full rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-1.5 text-sm font-medium text-surface">Open plan</button>
        </form>
      )}

      {pips.length === 0 && (
        <div className="rounded-xl border border-line bg-surface p-8 text-center text-sm text-mute shadow-sm">
          No improvement plans.
        </div>
      )}

      {pips.map((p) => (
        <section key={p.id} className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <div>
              <span className="text-sm font-semibold text-ink">{p.employee_name ?? p.employee_id}</span>
              <span className="ml-2 text-[11px] text-mute">{p.start_date} → {p.end_date}</span>
            </div>
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLE[p.status]}`}>
              {p.status}
            </span>
          </div>
          <div className="px-4 py-3 text-sm">
            <p className="text-ink"><span className="text-mute">Reason:</span> {p.reason}</p>
            <p className="mt-1 text-ink"><span className="text-mute">Objectives:</span> {p.objectives}</p>
            {p.checkpoints.length > 0 && (
              <div className="mt-3 space-y-1">
                <div className="text-[10px] font-semibold uppercase tracking-wide text-mute">Checkpoints</div>
                {p.checkpoints.map((c) => (
                  <div key={c.id} className="flex items-center gap-2 text-[12px]">
                    <span className={`font-medium capitalize ${RATING_STYLE[c.rating]}`}>{c.rating.replace("_", " ")}</span>
                    <span className="text-mute-2">{c.checkpoint_date}</span>
                    {c.note && <span className="text-mute">— {c.note}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
          {isHr && p.status === "active" && (
            <div className="flex justify-end gap-2 border-t border-line px-4 py-2.5">
              <button onClick={() => checkpoint(p.id)} className="rounded-md border border-line px-2.5 py-1 text-[11px] font-medium text-mute hover:text-ink">
                Add checkpoint
              </button>
              <button onClick={() => close(p.id)} className="rounded-md bg-ink px-3 py-1 text-[11px] font-medium text-surface">
                Close
              </button>
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
