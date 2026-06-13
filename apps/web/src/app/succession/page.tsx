"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addSuccessor,
  createKeyPosition,
  fetchEmployees,
  fetchKeyPositions,
  removeSuccessor,
  type EmployeeListItem,
  type KeyPosition,
} from "@/lib/api";

const RISK_STYLE: Record<string, string> = {
  high: "bg-red-soft text-red-strong",
  medium: "bg-warn-soft text-warn-strong",
  low: "bg-green-soft text-green-strong",
};
const BENCH_STYLE: Record<string, string> = {
  covered: "bg-green-soft text-green-strong",
  developing: "bg-blue-soft text-blue-strong",
  at_risk: "bg-red-soft text-red-strong",
};
const READINESS_LABEL: Record<string, string> = {
  ready_now: "Ready now",
  "1_2_years": "1–2 years",
  "3_5_years": "3–5 years",
};
const READINESS_STYLE: Record<string, string> = {
  ready_now: "bg-green-soft text-green-strong",
  "1_2_years": "bg-warn-soft text-warn-strong",
  "3_5_years": "bg-line-2 text-mute",
};

function PositionCard({
  pos,
  employees,
  onChanged,
  onError,
}: {
  pos: KeyPosition;
  employees: EmployeeListItem[];
  onChanged: () => void;
  onError: (m: string) => void;
}) {
  const [adding, setAdding] = useState(false);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await addSuccessor(pos.id, {
        employee_id: Number(fd.get("employee_id")),
        readiness: fd.get("readiness") as "ready_now" | "1_2_years" | "3_5_years",
        note: (fd.get("note") as string) || null,
      });
      form.reset();
      setAdding(false);
      onChanged();
    } catch (err) {
      onError((err as Error).message);
    }
  }
  async function remove(candidateId: string) {
    try {
      await removeSuccessor(pos.id, candidateId);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <div>
          <span className="text-sm font-semibold text-ink">{pos.title}</span>
          <span className="ml-2 text-[11px] text-mute">
            {pos.incumbent_name ? `incumbent: ${pos.incumbent_name}` : "vacant"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${RISK_STYLE[pos.risk_level]}`}>
            {pos.risk_level} risk
          </span>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${BENCH_STYLE[pos.bench_status]}`}>
            {pos.bench_status.replace("_", " ")}
          </span>
        </div>
      </div>
      <div className="divide-y divide-line-2">
        {pos.candidates.map((c) => (
          <div key={c.id} className="flex items-center justify-between px-4 py-2 text-sm">
            <span className="text-ink">
              {c.employee_name ?? c.employee_id}
              {c.note && <span className="ml-2 text-[11px] text-mute">{c.note}</span>}
            </span>
            <span className="flex items-center gap-2">
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${READINESS_STYLE[c.readiness]}`}>
                {READINESS_LABEL[c.readiness]}
              </span>
              <button onClick={() => remove(c.id)} className="text-[11px] text-mute hover:text-red-strong">
                remove
              </button>
            </span>
          </div>
        ))}
        {pos.candidates.length === 0 && (
          <p className="px-4 py-3 text-[12px] text-mute">No successors identified.</p>
        )}
      </div>
      <div className="border-t border-line px-4 py-2">
        {adding ? (
          <form onSubmit={add} className="flex flex-wrap items-end gap-2">
            <select name="employee_id" required defaultValue="" className="rounded-lg border border-line px-2 py-1.5 text-sm">
              <option value="" disabled>Successor…</option>
              {employees.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.full_name}</option>)}
            </select>
            <select name="readiness" defaultValue="1_2_years" className="rounded-lg border border-line px-2 py-1.5 text-sm">
              <option value="ready_now">Ready now</option>
              <option value="1_2_years">1–2 years</option>
              <option value="3_5_years">3–5 years</option>
            </select>
            <input name="note" placeholder="Note" className="min-w-32 flex-1 rounded-lg border border-line px-2 py-1.5 text-sm" />
            <button className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface">Add</button>
            <button type="button" onClick={() => setAdding(false)} className="text-xs text-mute">cancel</button>
          </form>
        ) : (
          <button onClick={() => setAdding(true)} className="text-xs font-medium text-blue-strong hover:underline">
            + Add successor
          </button>
        )}
      </div>
    </section>
  );
}

export default function SuccessionPage() {
  const [positions, setPositions] = useState<KeyPosition[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const reload = useCallback(() => {
    fetchKeyPositions().then(setPositions).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    reload();
    fetchEmployees({ limit: 500 }).then((r) => setEmployees(r.items)).catch(() => {});
  }, [reload]);

  async function addPosition(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await createKeyPosition({
        title: fd.get("title") as string,
        incumbent_id: fd.get("incumbent_id") ? Number(fd.get("incumbent_id")) : null,
        risk_level: fd.get("risk_level") as "low" | "medium" | "high",
      });
      form.reset();
      setAdding(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const atRisk = positions.filter((p) => p.bench_status === "at_risk").length;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Succession planning</h1>
          <p className="text-xs text-mute">Key positions · vacancy risk · successor bench strength</p>
        </div>
        <button onClick={() => setAdding(!adding)} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
          + Key position
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">Key positions</div>
          <div className="text-2xl font-semibold text-ink">{positions.length}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">At risk</div>
          <div className="text-2xl font-semibold text-red-strong">{atRisk}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">Covered</div>
          <div className="text-2xl font-semibold text-green">
            {positions.filter((p) => p.bench_status === "covered").length}
          </div>
        </div>
      </div>

      {adding && (
        <form onSubmit={addPosition} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <input name="title" required placeholder="Position title" className="rounded-lg border border-line px-3 py-2 text-sm" />
          <select name="incumbent_id" defaultValue="" className="rounded-lg border border-line px-2 py-2 text-sm">
            <option value="">Incumbent (optional)…</option>
            {employees.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.full_name}</option>)}
          </select>
          <select name="risk_level" defaultValue="medium" className="rounded-lg border border-line px-2 py-2 text-sm">
            <option value="low">Low risk</option>
            <option value="medium">Medium risk</option>
            <option value="high">High risk</option>
          </select>
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Add</button>
        </form>
      )}

      <div className="space-y-4">
        {positions.map((p) => (
          <PositionCard key={p.id} pos={p} employees={employees} onChanged={reload} onError={setError} />
        ))}
        {positions.length === 0 && (
          <div className="rounded-xl border border-line bg-surface p-8 text-center text-sm text-mute shadow-sm">
            No key positions defined yet.
          </div>
        )}
      </div>
    </div>
  );
}
