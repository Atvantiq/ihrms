"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  decideWeek,
  fetchEmployees,
  fetchMe,
  fetchProjects,
  fetchWeek,
  logHours,
  submitWeek,
  type EmployeeListItem,
  type Project,
  type TimesheetWeek,
} from "@/lib/api";

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function mondayOf(d: Date): string {
  const x = new Date(d);
  const day = (x.getDay() + 6) % 7; // 0 = Monday
  x.setDate(x.getDate() - day);
  return x.toISOString().slice(0, 10);
}
function shiftWeek(iso: string, weeks: number): string {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + weeks * 7);
  return mondayOf(d);
}

const STATUS_STYLE: Record<string, string> = {
  draft: "bg-line-2 text-mute",
  submitted: "bg-warn-soft text-warn-strong",
  approved: "bg-green-soft text-green-strong",
  rejected: "bg-red-soft text-red-strong",
};

export default function TimesheetPage() {
  const [weekOf, setWeekOf] = useState(() => mondayOf(new Date()));
  const [me, setMe] = useState<{ employee_id: number; is_hr: boolean } | null>(null);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [empId, setEmpId] = useState<number | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [week, setWeek] = useState<TimesheetWeek | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe().then((m) => {
      setMe({ employee_id: m.employee_id, is_hr: m.is_hr });
      setEmpId(m.employee_id);
      if (m.is_hr) fetchEmployees({}).then((d) => setEmployees(d.items)).catch(() => {});
    });
    fetchProjects().then(setProjects).catch(() => {});
  }, []);

  const reload = useCallback(() => {
    if (!empId) return;
    fetchWeek(weekOf, empId).then(setWeek).catch((e) => setError(e.message));
  }, [weekOf, empId]);

  useEffect(reload, [reload]);

  const isOwn = me && empId === me.employee_id;
  const editable = week?.status === "draft" || week?.status === "rejected";

  // hours lookup: project_id|date -> hours
  const cell = useMemo(() => {
    const map = new Map<string, string>();
    week?.entries.forEach((e) => map.set(`${e.project_id}|${e.work_date}`, e.hours));
    return map;
  }, [week]);

  async function setHours(projectId: string, dateIso: string, value: string) {
    const h = Number(value);
    if (Number.isNaN(h) || h < 0 || h > 24) return;
    try {
      const updated = await logHours(projectId, dateIso, h);
      setWeek(updated);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function submit() {
    try {
      setWeek(await submitWeek(weekOf));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function decide(action: "approve" | "reject") {
    if (!week) return;
    const note = action === "reject" ? window.prompt("Reason?") ?? undefined : undefined;
    try {
      setWeek(await decideWeek(action, week.employee_id, weekOf, note));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function dayTotal(dateIso: string): number {
    return projects.reduce(
      (s, p) => s + Number(cell.get(`${p.id}|${dateIso}`) ?? 0),
      0,
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Timesheet</h1>
          <p className="text-xs text-mute">
            Log hours per project · submit the week for approval
          </p>
        </div>
        <div className="flex items-center gap-2">
          {me?.is_hr && employees.length > 0 && (
            <select
              value={empId ?? ""}
              onChange={(e) => setEmpId(Number(e.target.value))}
              className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"
            >
              {employees.map((m) => (
                <option key={m.employee_id} value={m.employee_id}>{m.full_name}</option>
              ))}
            </select>
          )}
          <button
            onClick={() => setWeekOf(shiftWeek(weekOf, -1))}
            className="rounded-lg border border-line px-2.5 py-1.5 text-sm text-mute hover:text-ink"
          >
            ‹
          </button>
          <span className="text-sm font-medium text-ink">Week of {weekOf}</span>
          <button
            onClick={() => setWeekOf(shiftWeek(weekOf, 1))}
            className="rounded-lg border border-line px-2.5 py-1.5 text-sm text-mute hover:text-ink"
          >
            ›
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}{" "}
          <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {week && (
        <section className="overflow-x-auto rounded-xl border border-line bg-surface shadow-sm">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-ink">
                {week.total_hours}h total
              </span>
              {Number(week.overtime) > 0 && (
                <span className="text-xs text-warn-strong">
                  +{week.overtime}h overtime
                </span>
              )}
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLE[week.status]}`}
              >
                {week.status}
              </span>
              {week.approver_name && (
                <span className="text-[11px] text-mute-2">by {week.approver_name}</span>
              )}
            </div>
            <div className="flex gap-2">
              {isOwn && editable && (
                <button
                  onClick={submit}
                  className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2"
                >
                  Submit week
                </button>
              )}
              {week.can_decide && (
                <>
                  <button
                    onClick={() => decide("approve")}
                    className="rounded-lg bg-green-soft px-3 py-1.5 text-xs font-medium text-green-strong"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => decide("reject")}
                    className="rounded-lg bg-red-soft px-3 py-1.5 text-xs font-medium text-red-strong"
                  >
                    Reject
                  </button>
                </>
              )}
            </div>
          </div>

          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
                <th className="px-4 py-2 font-semibold">Project</th>
                {week.dates.map((d, i) => (
                  <th key={d} className="px-2 py-2 text-center font-semibold">
                    {DOW[i]}<br />
                    <span className="font-normal text-mute-2">{d.slice(8)}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="border-b border-line-2 last:border-0">
                  <td className="px-4 py-2">
                    <div className="font-medium text-ink">{p.code}</div>
                    <div className="text-[10px] text-mute">{p.name}</div>
                  </td>
                  {week.dates.map((d) => (
                    <td key={d} className="px-1 py-1 text-center">
                      <input
                        type="number"
                        min={0}
                        max={24}
                        step={0.5}
                        disabled={!isOwn || !editable}
                        defaultValue={cell.get(`${p.id}|${d}`) ?? ""}
                        onBlur={(e) => {
                          if (e.target.value !== "") setHours(p.id, d, e.target.value);
                        }}
                        className="w-12 rounded-md border border-line bg-surface px-1 py-1 text-center text-sm outline-none focus:border-indigo disabled:bg-line-2/40"
                      />
                    </td>
                  ))}
                </tr>
              ))}
              <tr className="bg-canvas font-medium">
                <td className="px-4 py-2 text-[11px] uppercase tracking-wide text-mute">
                  Daily total
                </td>
                {week.dates.map((d) => (
                  <td key={d} className="px-2 py-2 text-center text-ink">
                    {dayTotal(d) || ""}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
