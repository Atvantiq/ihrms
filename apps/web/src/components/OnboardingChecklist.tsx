"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchOnboarding,
  toggleOnboardingTask,
  type OnboardingChecklist as Checklist,
} from "@/lib/api";

const ROLE_STYLE: Record<string, string> = {
  hr: "bg-indigo-soft text-indigo-strong",
  manager: "bg-blue-soft text-blue-strong",
  it: "bg-warn-soft text-warn-strong",
  employee: "bg-green-soft text-green-strong",
};

export function OnboardingChecklist({
  employeeId,
  canEdit = true,
}: {
  employeeId: number;
  canEdit?: boolean;
}) {
  const [data, setData] = useState<Checklist | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchOnboarding(employeeId).then(setData).catch((e) => setError(e.message));
  }, [employeeId]);
  useEffect(() => reload(), [reload]);

  async function toggle(taskId: string) {
    try {
      setData(await toggleOnboardingTask(employeeId, taskId));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // nothing to show until a checklist has been generated for this hire
  if (!data || data.total === 0) return null;

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <h2 className="text-sm font-semibold text-ink">Onboarding checklist</h2>
        <span className="flex items-center gap-2 text-[11px] text-mute">
          {data.done}/{data.total} done
          <span className="h-1.5 w-24 overflow-hidden rounded-full bg-line-2">
            <span
              className={`block h-1.5 rounded-full ${data.pct === 100 ? "bg-green" : "bg-indigo"}`}
              style={{ width: `${data.pct}%` }}
            />
          </span>
          <span className="font-semibold text-ink">{data.pct}%</span>
        </span>
      </div>
      {error && (
        <div className="border-b border-line bg-red-soft/30 px-4 py-2 text-xs text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}
      <div className="divide-y divide-line-2">
        {data.tasks.map((t) => (
          <label key={t.id} className="flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm">
            <input
              type="checkbox"
              checked={t.status === "done"}
              disabled={!canEdit}
              onChange={() => toggle(t.id)}
            />
            <span className={`flex-1 ${t.status === "done" ? "text-mute line-through" : "text-ink"}`}>
              {t.title}
            </span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${ROLE_STYLE[t.owner_role] ?? "bg-line-2 text-mute"}`}>
              {t.owner_role}
            </span>
            {t.completed_on && <span className="text-[10px] text-mute-2">{t.completed_on}</span>}
          </label>
        ))}
      </div>
    </section>
  );
}
