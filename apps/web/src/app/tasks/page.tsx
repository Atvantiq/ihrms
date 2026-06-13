"use client";

import { useCallback, useEffect, useState } from "react";
import {
  approveIncrement,
  decideClaim,
  decideCompOff,
  decideDuty,
  decideLeave,
  decideOvertime,
  decideRegularization,
  decideWeek,
  fetchTasks,
  type Task,
} from "@/lib/api";
import { Avatar } from "@/components/Avatar";

const TYPE_META: Record<Task["task_type"], { label: string; tone: string }> = {
  leave: { label: "Leave", tone: "bg-indigo-soft text-indigo-strong" },
  timesheet: { label: "Timesheet", tone: "bg-blue-soft text-blue-strong" },
  increment: { label: "Increment", tone: "bg-green-soft text-green-strong" },
  regularization: { label: "Attendance", tone: "bg-warn-soft text-warn-strong" },
  overtime: { label: "Overtime", tone: "bg-pink-soft text-pink-strong" },
  comp_off: { label: "Comp-off", tone: "bg-blue-soft text-blue-strong" },
  duty: { label: "WFH / on-duty", tone: "bg-indigo-soft text-indigo-strong" },
  claim: { label: "Expense claim", tone: "bg-green-soft text-green-strong" },
};

const ORDER: Task["task_type"][] = [
  "leave", "timesheet", "regularization", "overtime", "comp_off", "duty", "claim", "increment",
];

function taskKey(t: Task): string {
  return `${t.task_type}:${t.ref_id}`;
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchTasks()
      .then(setTasks)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => reload(), [reload]);

  async function act(t: Task, action: "approve" | "reject") {
    setBusy(taskKey(t));
    setError(null);
    try {
      if (t.task_type === "leave") {
        await decideLeave(t.ref_id, action);
      } else if (t.task_type === "timesheet") {
        await decideWeek(action, t.employee_id, t.week_of ?? "");
      } else if (t.task_type === "increment" && action === "approve") {
        await approveIncrement(t.ref_id);
      } else if (t.task_type === "regularization") {
        await decideRegularization(t.ref_id, action);
      } else if (t.task_type === "overtime") {
        await decideOvertime(t.ref_id, action);
      } else if (t.task_type === "comp_off") {
        await decideCompOff(t.ref_id, action);
      } else if (t.task_type === "duty") {
        await decideDuty(t.ref_id, action);
      } else if (t.task_type === "claim") {
        await decideClaim(t.ref_id, action);
      }
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const grouped = ORDER.map((type) => ({
    type,
    items: (tasks ?? []).filter((t) => t.task_type === type),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-ink">Tasks</h1>
        <p className="text-xs text-mute">
          Everything waiting on your decision, across modules
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}{" "}
          <button onClick={() => setError(null)} className="underline">
            dismiss
          </button>
        </div>
      )}

      {tasks !== null && grouped.length === 0 && (
        <div className="rounded-xl border border-line bg-surface p-8 text-center text-sm text-mute shadow-sm">
          You&apos;re all caught up — nothing awaiting your decision. 🎉
        </div>
      )}

      {grouped.map((g) => (
        <section
          key={g.type}
          className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm"
        >
          <div className="flex items-center gap-2 border-b border-line px-4 py-2.5">
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${TYPE_META[g.type].tone}`}
            >
              {TYPE_META[g.type].label}
            </span>
            <span className="text-xs text-mute">{g.items.length} pending</span>
          </div>
          <div className="divide-y divide-line-2">
            {g.items.map((t) => {
              const isBusy = busy === taskKey(t);
              return (
                <div key={taskKey(t)} className="flex items-center gap-3 px-4 py-3">
                  <Avatar name={t.employee_name} size={30} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-ink">{t.employee_name}</span>
                      <span className="rounded bg-line-2 px-1.5 py-0.5 font-mono text-[10px] text-mute">
                        {t.badge}
                      </span>
                    </div>
                    <div className="text-xs text-ink">{t.title}</div>
                    <div className="text-[11px] text-mute">{t.subtitle}</div>
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    {t.can_reject && (
                      <button
                        disabled={isBusy}
                        onClick={() => act(t, "reject")}
                        className="rounded-md border border-line px-2.5 py-1 text-[11px] font-medium text-mute hover:text-red-strong disabled:opacity-50"
                      >
                        Reject
                      </button>
                    )}
                    <button
                      disabled={isBusy}
                      onClick={() => act(t, "approve")}
                      className="rounded-md bg-ink px-3 py-1 text-[11px] font-medium text-surface hover:bg-ink-2 disabled:opacity-50"
                    >
                      {isBusy ? "…" : "Approve"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
