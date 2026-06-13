"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  addHoliday,
  deleteHoliday,
  fetchHolidays,
  fetchMe,
  type Holiday,
} from "@/lib/api";

const TYPE_STYLES: Record<string, string> = {
  public: "bg-indigo-soft text-indigo-strong",
  optional: "bg-warn-soft text-warn-strong",
  restricted: "bg-line-2 text-mute",
};

const WEEKDAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function HolidaysPage() {
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [year, setYear] = useState(2026);
  const [isHr, setIsHr] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchHolidays(year)
      .then(setHolidays)
      .catch((e: Error) => setError(e.message));
  }, [year]);

  useEffect(() => {
    fetchMe()
      .then((me) => setIsHr(me.is_hr))
      .catch(() => {});
  }, []);
  useEffect(reload, [reload]);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await addHoliday(
        (fd.get("name") as string).trim(),
        fd.get("holiday_date") as string,
        fd.get("type") as Holiday["type"],
      );
      (e.target as HTMLFormElement).reset();
      setError(null);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function remove(h: Holiday) {
    if (!window.confirm(`Remove "${h.name}" (${h.holiday_date})?`)) return;
    try {
      await deleteHoliday(h.id);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 space-y-4 p-6">
      <div>
        <Link href="/leave" className="text-xs text-mute hover:text-ink">
          ← Leave
        </Link>
        <div className="mt-1 flex items-end justify-between">
          <div>
            <h1 className="text-xl font-semibold text-ink">Holiday calendar</h1>
            <p className="text-xs text-mute">
              Public holidays are excluded from leave working-day counts.
            </p>
          </div>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"
          >
            {[2025, 2026, 2027].map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}{" "}
          <button onClick={() => setError(null)} className="underline">
            dismiss
          </button>
        </div>
      )}

      {isHr && (
        <form
          onSubmit={add}
          className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm"
        >
          <div className="flex-1 min-w-40">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
              Holiday name
            </label>
            <input
              name="name"
              required
              placeholder="e.g. Diwali"
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-indigo"
            />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
              Date
            </label>
            <input
              name="holiday_date"
              type="date"
              required
              className="rounded-lg border border-line bg-surface px-2 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
              Type
            </label>
            <select
              name="type"
              className="rounded-lg border border-line bg-surface px-2 py-2 text-sm"
            >
              <option value="public">Public</option>
              <option value="optional">Optional</option>
              <option value="restricted">Restricted</option>
            </select>
          </div>
          <button
            type="submit"
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface hover:bg-ink-2"
          >
            Add holiday
          </button>
        </form>
      )}

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
          {year} holidays{" "}
          <span className="font-normal text-mute">({holidays.length})</span>
        </div>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">Date</th>
              <th className="px-3 py-2 font-semibold">Day</th>
              <th className="px-3 py-2 font-semibold">Holiday</th>
              <th className="px-3 py-2 font-semibold">Type</th>
              {isHr && <th className="px-3 py-2"></th>}
            </tr>
          </thead>
          <tbody>
            {holidays.map((h) => {
              const d = new Date(h.holiday_date + "T00:00:00");
              return (
                <tr key={h.id} className="border-b border-line-2 last:border-0">
                  <td className="px-4 py-2 font-mono text-xs text-ink">
                    {h.holiday_date}
                  </td>
                  <td className="px-3 py-2 text-mute">{WEEKDAY[d.getDay()]}</td>
                  <td className="px-3 py-2 font-medium text-ink">{h.name}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded-md px-1.5 py-0.5 text-[10px] font-medium capitalize ${TYPE_STYLES[h.type]}`}
                    >
                      {h.type}
                    </span>
                  </td>
                  {isHr && (
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => remove(h)}
                        className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-red-strong"
                      >
                        Remove
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
            {holidays.length === 0 && (
              <tr>
                <td
                  colSpan={isHr ? 5 : 4}
                  className="px-4 py-8 text-center text-mute"
                >
                  No holidays for {year} yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
