"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addPlanAction,
  createDevelopmentPlan,
  fetchDevelopmentPlans,
  setPlanStatus,
  togglePlanAction,
  type DevelopmentPlan,
} from "@/lib/api";

const STATUS_STYLE: Record<string, string> = {
  active: "bg-blue-soft text-blue-strong",
  achieved: "bg-green-soft text-green-strong",
  dropped: "bg-line-2 text-mute",
};

export function DevelopmentPlans({
  employeeId,
  canEdit = true,
  title = "Development plans",
}: {
  employeeId?: number;
  canEdit?: boolean;
  title?: string;
}) {
  const [plans, setPlans] = useState<DevelopmentPlan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const reload = useCallback(() => {
    fetchDevelopmentPlans(employeeId).then(setPlans).catch((e) => setError(e.message));
  }, [employeeId]);
  useEffect(() => reload(), [reload]);

  async function act(fn: () => Promise<unknown>) {
    try {
      await fn();
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await createDevelopmentPlan({
        employee_id: employeeId,
        focus_area: fd.get("focus_area") as string,
        objective: fd.get("objective") as string,
        target_date: (fd.get("target_date") as string) || null,
      });
      form.reset();
      setAdding(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <h2 className="text-sm font-semibold text-ink">
          {title} <span className="font-normal text-mute">({plans.length})</span>
        </h2>
        {canEdit && (
          <button
            onClick={() => setAdding(!adding)}
            className="text-xs font-medium text-blue-strong hover:underline"
          >
            {adding ? "Cancel" : "+ New plan"}
          </button>
        )}
      </div>

      {error && (
        <div className="border-b border-line bg-red-soft/30 px-4 py-2 text-xs text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {adding && (
        <form onSubmit={create} className="flex flex-wrap items-end gap-2 border-b border-line bg-canvas p-3">
          <input name="focus_area" required placeholder="Focus area" className="rounded-lg border border-line px-2 py-1.5 text-sm" />
          <input name="objective" required placeholder="Objective" className="min-w-44 flex-1 rounded-lg border border-line px-2 py-1.5 text-sm" />
          <input name="target_date" type="date" className="rounded-lg border border-line px-2 py-1.5 text-sm" />
          <button className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface">Add</button>
        </form>
      )}

      <div className="divide-y divide-line-2">
        {plans.map((p) => {
          const done = p.actions.filter((a) => a.status === "done").length;
          return (
            <div key={p.id} className="px-4 py-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-ink">{p.focus_area}</span>
                  <span className="ml-2 text-[11px] text-mute">{p.objective}</span>
                </div>
                <div className="flex items-center gap-2">
                  {p.target_date && (
                    <span className="text-[10px] text-mute-2">by {p.target_date}</span>
                  )}
                  {canEdit && p.status === "active" ? (
                    <select
                      value={p.status}
                      onChange={(e) =>
                        act(() => setPlanStatus(p.id, e.target.value as "active" | "achieved" | "dropped"))
                      }
                      className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLE[p.status]}`}
                    >
                      <option value="active">active</option>
                      <option value="achieved">achieved</option>
                      <option value="dropped">dropped</option>
                    </select>
                  ) : (
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${STATUS_STYLE[p.status]}`}>
                      {p.status}
                    </span>
                  )}
                </div>
              </div>

              {p.actions.length > 0 && (
                <div className="mt-2 space-y-1">
                  {p.actions.map((a) => (
                    <label key={a.id} className="flex cursor-pointer items-center gap-2 text-[13px]">
                      <input
                        type="checkbox"
                        checked={a.status === "done"}
                        disabled={!canEdit}
                        onChange={() => act(() => togglePlanAction(p.id, a.id))}
                      />
                      <span className={a.status === "done" ? "text-mute line-through" : "text-ink"}>
                        {a.action}
                      </span>
                    </label>
                  ))}
                  <div className="text-[10px] text-mute-2">{done}/{p.actions.length} actions done</div>
                </div>
              )}

              {canEdit && p.status === "active" && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const fd = new FormData(e.currentTarget);
                    const t = (fd.get("action") as string).trim();
                    if (t) act(() => addPlanAction(p.id, t));
                    e.currentTarget.reset();
                  }}
                  className="mt-2 flex gap-2"
                >
                  <input name="action" placeholder="Add action…" className="flex-1 rounded-lg border border-line px-2 py-1 text-xs" />
                  <button className="rounded-lg border border-line px-2 py-1 text-xs text-mute hover:text-ink">Add</button>
                </form>
              )}
            </div>
          );
        })}
        {plans.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-mute">No development plans yet.</div>
        )}
      </div>
    </section>
  );
}
