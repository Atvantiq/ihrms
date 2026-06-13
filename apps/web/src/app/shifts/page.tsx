"use client";

import { useCallback, useEffect, useState } from "react";
import {
  assignShift,
  createShift,
  fetchRoster,
  fetchShifts,
  type RosterRow,
  type Shift,
} from "@/lib/api";

export default function ShiftsPage() {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [roster, setRoster] = useState<RosterRow[]>([]);
  const [on, setOn] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const reloadRoster = useCallback(() => {
    fetchRoster(on).then(setRoster).catch((e) => setError(e.message));
  }, [on]);

  useEffect(() => {
    fetchShifts().then(setShifts).catch((e) => setError(e.message));
  }, []);
  useEffect(() => reloadRoster(), [reloadRoster]);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await createShift({
        code: fd.get("code") as string,
        name: fd.get("name") as string,
        start_time: fd.get("start_time") as string,
        end_time: fd.get("end_time") as string,
        break_minutes: Number(fd.get("break_minutes") || 0),
      });
      form.reset();
      setShowAdd(false);
      fetchShifts().then(setShifts).catch(() => {});
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function assign(employeeId: number, shiftId: string) {
    try {
      await assignShift(employeeId, shiftId, on);
      reloadRoster();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Shifts &amp; roster</h1>
          <p className="text-xs text-mute">Define shifts · assign them · see who&apos;s on which shift</p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
          + New shift
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {showAdd && (
        <form onSubmit={add} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <input name="code" required placeholder="Code" className="w-24 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="name" required placeholder="Name" className="min-w-40 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
            Start
            <input name="start_time" type="time" required defaultValue="09:30" className="mt-1 block rounded-lg border border-line px-2 py-1.5 text-sm" />
          </label>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
            End
            <input name="end_time" type="time" required defaultValue="18:30" className="mt-1 block rounded-lg border border-line px-2 py-1.5 text-sm" />
          </label>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
            Break (min)
            <input name="break_minutes" type="number" min="0" defaultValue="60" className="mt-1 block w-20 rounded-lg border border-line px-2 py-1.5 text-sm" />
          </label>
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Create</button>
        </form>
      )}

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
          Shifts <span className="font-normal text-mute">({shifts.length})</span>
        </div>
        <div className="divide-y divide-line-2">
          {shifts.map((s) => (
            <div key={s.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <span className="text-ink">
                <span className="font-mono text-[11px] text-mute">{s.code}</span>
                <span className="ml-2 font-medium">{s.name}</span>
                {s.is_night && (
                  <span className="ml-2 rounded-full bg-indigo-soft px-1.5 py-0.5 text-[9px] font-semibold uppercase text-indigo-strong">
                    night
                  </span>
                )}
              </span>
              <span className="text-[11px] text-mute">
                {s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)} · {s.break_minutes}m break ·{" "}
                <span className="font-semibold text-ink">{s.hours}h</span>
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <span className="text-sm font-semibold text-ink">Roster</span>
          <input
            type="date"
            value={on}
            onChange={(e) => setOn(e.target.value)}
            className="rounded-lg border border-line px-2 py-1 text-sm text-mute"
          />
        </div>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">Employee</th>
              <th className="px-3 py-2 font-semibold">Shift</th>
              <th className="px-3 py-2 text-right font-semibold">Assign</th>
            </tr>
          </thead>
          <tbody>
            {roster.map((r) => (
              <tr key={r.employee_id} className="border-b border-line-2 last:border-0">
                <td className="px-4 py-2 text-ink">{r.employee_name}</td>
                <td className="px-3 py-2">
                  {r.shift_code ? (
                    <span className="rounded-full bg-blue-soft px-2 py-0.5 text-[11px] font-medium text-blue-strong">
                      {r.shift_name}
                    </span>
                  ) : (
                    <span className="text-[11px] text-mute-2">— unassigned</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  <select
                    defaultValue=""
                    onChange={(e) => e.target.value && assign(r.employee_id, e.target.value)}
                    className="rounded-md border border-line px-2 py-1 text-[11px]"
                  >
                    <option value="">Set shift…</option>
                    {shifts.map((s) => (
                      <option key={s.id} value={s.id}>{s.code}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
