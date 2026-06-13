"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addGoal,
  approveIncrement,
  createCycle,
  enrollCycle,
  fetchCalibration,
  fetchCycleReviews,
  fetchCycles,
  fetchGoals,
  fetchMe,
  fetchMyReviews,
  proposeIncrement,
  publishReview,
  pushIncrement,
  submitManagerReview,
  submitSelfReview,
  updateGoal,
  type Calibration,
  type Goal,
  type Review,
  type ReviewCycle,
} from "@/lib/api";

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

const REVIEW_STATUS: Record<string, string> = {
  pending: "bg-line-2 text-mute",
  self_done: "bg-blue-soft text-blue-strong",
  manager_done: "bg-warn-soft text-warn-strong",
  published: "bg-green-soft text-green-strong",
};

function Stars({ n }: { n: number | null }) {
  return <span className="text-amber">{n ? "★".repeat(n) : "—"}</span>;
}

function CycleReviews({ cycleId, onError }: { cycleId: string; onError: (m: string) => void }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchCycleReviews(cycleId).then(setReviews).catch((e) => onError(e.message));
  }, [cycleId, onError]);
  useEffect(reload, [reload]);

  async function manager(r: Review) {
    const rating = Number(window.prompt(`Manager rating for ${r.employee_name} (1-5)?`, "4"));
    if (!rating) return;
    const pot = Number(window.prompt("Potential (1-5)?", "4"));
    if (!pot) return;
    try {
      await submitManagerReview(r.id, rating, pot);
      reload();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function publish(r: Review) {
    try {
      await publishReview(r.id);
      reload();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function increment(r: Review) {
    try {
      const inc = await proposeIncrement(r.id);
      if (
        window.confirm(
          `Increment ${r.employee_name}: ${inr(inc.current_ctc)} → ${inr(inc.proposed_ctc)} (+${inc.pct}%)?\nApprove & push into payroll?`,
        )
      ) {
        await approveIncrement(inc.id);
        await pushIncrement(inc.id);
        setMsg(`Pushed ${r.employee_name}'s increment into payroll ✓`);
        setTimeout(() => setMsg(null), 3000);
      }
    } catch (e) {
      onError((e as Error).message);
    }
  }

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <span className="text-sm font-semibold text-ink">
          Reviews <span className="font-normal text-mute">({reviews.length})</span>
        </span>
        {msg && <span className="text-xs text-green-strong">{msg}</span>}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">Employee</th>
              <th className="px-3 py-2 font-semibold">Self</th>
              <th className="px-3 py-2 font-semibold">Manager</th>
              <th className="px-3 py-2 font-semibold">Final</th>
              <th className="px-3 py-2 font-semibold">9-box</th>
              <th className="px-3 py-2 font-semibold">Status</th>
              <th className="px-3 py-2 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {reviews.map((r) => (
              <tr key={r.id} className="border-b border-line-2 last:border-0">
                <td className="px-4 py-2 font-medium text-ink">{r.employee_name}</td>
                <td className="px-3 py-2"><Stars n={r.self_rating} /></td>
                <td className="px-3 py-2"><Stars n={r.manager_rating} /></td>
                <td className="px-3 py-2"><Stars n={r.final_rating} /></td>
                <td className="px-3 py-2 text-xs text-mute">
                  {r.nine_box ? `${r.nine_box} · ${r.nine_box_label}` : "—"}
                </td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${REVIEW_STATUS[r.status]}`}>
                    {r.status.replace("_", " ")}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1.5">
                    {r.status === "self_done" && (
                      <button onClick={() => manager(r)} className="rounded-md bg-warn-soft px-2 py-1 text-[11px] font-medium text-warn-strong">
                        Rate
                      </button>
                    )}
                    {r.status === "manager_done" && (
                      <button onClick={() => publish(r)} className="rounded-md bg-green-soft px-2 py-1 text-[11px] font-medium text-green-strong">
                        Publish
                      </button>
                    )}
                    {r.status === "published" && (
                      <button onClick={() => increment(r)} className="rounded-md bg-ink px-2 py-1 text-[11px] font-medium text-surface">
                        Increment
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {reviews.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-mute">
                  No reviews — enroll the cycle.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function MyPanel({ onError }: { onError: (m: string) => void }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);

  const reload = useCallback(() => {
    fetchMyReviews().then(setReviews).catch(() => {});
    fetchGoals().then(setGoals).catch(() => {});
  }, []);
  useEffect(reload, [reload]);

  async function selfRate(r: Review) {
    const rating = Number(window.prompt("Your self-rating (1-5)?", "4"));
    if (!rating) return;
    try {
      await submitSelfReview(r.id, rating, window.prompt("Comment?") ?? undefined);
      reload();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function newGoal(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await addGoal(fd.get("title") as string);
      (e.target as HTMLFormElement).reset();
      reload();
    } catch (err) {
      onError((err as Error).message);
    }
  }
  async function setProgress(g: Goal, p: number) {
    try {
      await updateGoal(g.id, p, p >= 100 ? "done" : "active");
      reload();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
          My reviews
        </div>
        <div className="divide-y divide-line-2">
          {reviews.map((r) => (
            <div key={r.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <span>
                <span className="text-ink">{r.status.replace("_", " ")}</span>
                {r.final_rating && (
                  <span className="ml-2 text-amber">{"★".repeat(r.final_rating)}</span>
                )}
              </span>
              {r.can_self && (
                <button onClick={() => selfRate(r)} className="rounded-md bg-ink px-2 py-1 text-[11px] font-medium text-surface">
                  Self-rate
                </button>
              )}
            </div>
          ))}
          {reviews.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-mute">No reviews yet.</div>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
          My goals
        </div>
        <form onSubmit={newGoal} className="flex gap-2 border-b border-line bg-canvas px-4 py-2.5">
          <input name="title" required placeholder="New goal…" className="flex-1 rounded-lg border border-line px-3 py-1.5 text-sm" />
          <button className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface">+ Add</button>
        </form>
        <div className="divide-y divide-line-2">
          {goals.map((g) => (
            <div key={g.id} className="px-4 py-2.5 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-ink">{g.title}</span>
                <span className="text-xs text-mute">{g.progress}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={10}
                defaultValue={g.progress}
                onMouseUp={(e) => setProgress(g, Number((e.target as HTMLInputElement).value))}
                className="mt-1 w-full"
              />
            </div>
          ))}
          {goals.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-mute">No goals yet.</div>
          )}
        </div>
      </section>
    </div>
  );
}

function CalibrationPanel({ cycleId, onError }: { cycleId: string; onError: (m: string) => void }) {
  const [cal, setCal] = useState<Calibration | null>(null);
  useEffect(() => {
    fetchCalibration(cycleId).then(setCal).catch((e) => onError(e.message));
  }, [cycleId, onError]);
  if (!cal) return null;

  const maxPct = Math.max(
    1,
    ...cal.buckets.flatMap((b) => [Number(b.actual_pct), Number(b.target_pct)]),
  );
  return (
    <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">Calibration · forced distribution</h2>
        <span className="text-[11px] text-mute">
          {cal.rated_count} rated · {cal.pending_count} pending
        </span>
      </div>
      <div className="space-y-2.5">
        {cal.buckets.map((b) => {
          const delta = Number(b.delta_pct);
          return (
            <div key={b.rating} className="flex items-center gap-3 text-sm">
              <span className="w-28 shrink-0 text-mute">
                <span className="text-amber">{"★".repeat(b.rating)}</span>{" "}
                <span className="text-[11px]">{b.label}</span>
              </span>
              <div className="relative h-5 flex-1 rounded bg-line-2">
                {/* target marker */}
                <div
                  className="absolute top-0 h-5 w-0.5 bg-ink/40"
                  style={{ left: `${(Number(b.target_pct) / maxPct) * 100}%` }}
                  title={`target ${b.target_pct}%`}
                />
                <div
                  className="h-5 rounded bg-indigo"
                  style={{ width: `${(Number(b.actual_pct) / maxPct) * 100}%` }}
                />
              </div>
              <span className="w-10 text-right font-mono text-[11px] text-ink">{b.count}</span>
              <span
                className={`w-16 text-right font-mono text-[11px] ${
                  delta > 0 ? "text-warn-strong" : delta < 0 ? "text-blue-strong" : "text-mute-2"
                }`}
              >
                {delta > 0 ? "+" : ""}
                {b.delta_pct}%
              </span>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-[10px] text-mute-2">
        Bars show the cohort&apos;s manager-rating spread; the tick marks the target curve.
        Positive delta = over-represented vs target. Adjust at publish (final rating override).
      </p>
    </section>
  );
}

export default function PerformancePage() {
  const [isHr, setIsHr] = useState(false);
  const [cycles, setCycles] = useState<ReviewCycle[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [calibrating, setCalibrating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reloadCycles = useCallback(() => {
    fetchCycles().then(setCycles).catch(() => {});
  }, []);

  useEffect(() => {
    fetchMe().then((m) => {
      setIsHr(m.is_hr);
      if (m.is_hr) reloadCycles();
    });
  }, [reloadCycles]);

  async function newCycle() {
    const name = window.prompt("Cycle name?", "FY25-26 Annual");
    if (!name) return;
    try {
      const c = await createCycle(name, new Date().getFullYear());
      await enrollCycle(c.id);
      reloadCycles();
      setSelected(c.id);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function enroll(id: string) {
    try {
      await enrollCycle(id);
      reloadCycles();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Performance &amp; Growth</h1>
          <p className="text-xs text-mute">
            Goals · review cycles · 9-box · increments → payroll
          </p>
        </div>
        {isHr && (
          <button onClick={newCycle} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
            + New cycle
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {isHr && cycles.length > 0 && (
        <section className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
            Review cycles
          </div>
          <div className="divide-y divide-line-2">
            {cycles.map((c) => (
              <div key={c.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <button onClick={() => setSelected(selected === c.id ? null : c.id)} className="text-left">
                  <span className="font-medium text-ink">{c.name}</span>
                  <span className="ml-2 text-[10px] text-mute">
                    {c.period_year} · {c.review_count} reviews · {c.status}
                  </span>
                </button>
                <div className="flex gap-2">
                  <button onClick={() => enroll(c.id)} className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-ink">
                    Enroll all
                  </button>
                  <button onClick={() => setCalibrating(calibrating === c.id ? null : c.id)} className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-ink">
                    {calibrating === c.id ? "Hide" : "Calibrate"}
                  </button>
                  <button onClick={() => setSelected(selected === c.id ? null : c.id)} className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-ink">
                    {selected === c.id ? "Hide" : "Reviews"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {isHr && calibrating && <CalibrationPanel cycleId={calibrating} onError={setError} />}

      {isHr && selected && <CycleReviews cycleId={selected} onError={setError} />}

      <MyPanel onError={setError} />
    </div>
  );
}
