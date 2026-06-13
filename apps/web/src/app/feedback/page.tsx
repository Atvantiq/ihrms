"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchBadges,
  fetchEmployees,
  fetchGiven,
  fetchReceived,
  fetchWall,
  giveFeedback,
  type EmployeeListItem,
  type Feedback,
} from "@/lib/api";
import { Avatar } from "@/components/Avatar";

function timeAgo(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function FeedbackRow({ f, dir }: { f: Feedback; dir: "to" | "from" }) {
  const who = dir === "to" ? f.from_name : f.to_name;
  return (
    <div className="flex gap-3 px-4 py-3">
      <Avatar name={who ?? "—"} size={30} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-ink">{who ?? "—"}</span>
          {f.badge && (
            <span className="rounded-full bg-green-soft px-2 py-0.5 text-[10px] font-semibold capitalize text-green-strong">
              {f.badge}
            </span>
          )}
          <span className="text-[10px] text-mute-2">{timeAgo(f.created_at)}</span>
        </div>
        <p className="text-sm text-ink">{f.message}</p>
      </div>
    </div>
  );
}

export default function FeedbackPage() {
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [badges, setBadges] = useState<string[]>([]);
  const [wall, setWall] = useState<Feedback[]>([]);
  const [received, setReceived] = useState<Feedback[]>([]);
  const [given, setGiven] = useState<Feedback[]>([]);
  const [kind, setKind] = useState<"feedback" | "recognition">("recognition");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchWall().then(setWall).catch(() => {});
    fetchReceived().then(setReceived).catch(() => {});
    fetchGiven().then(setGiven).catch(() => {});
  }, []);

  useEffect(() => {
    reload();
    fetchEmployees({ limit: 500 }).then((r) => setEmployees(r.items)).catch(() => {});
    fetchBadges().then(setBadges).catch(() => {});
  }, [reload]);

  async function send(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await giveFeedback({
        to_employee_id: Number(fd.get("to_employee_id")),
        kind,
        badge: kind === "recognition" ? (fd.get("badge") as string) : null,
        visibility: kind === "recognition" ? "public" : "private",
        message: fd.get("message") as string,
      });
      form.reset();
      setMsg(kind === "recognition" ? "Recognition posted" : "Feedback sent");
      setTimeout(() => setMsg(null), 3000);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-ink">Feedback &amp; recognition</h1>
        <p className="text-xs text-mute">Give a colleague a shout-out or private feedback</p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}
      {msg && (
        <div className="rounded-xl border border-green-soft bg-green-soft/40 p-3 text-sm text-green-strong">{msg}</div>
      )}

      <form onSubmit={send} className="space-y-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-1 rounded-lg border border-line p-0.5">
            {(["recognition", "feedback"] as const).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                className={`rounded-md px-3 py-1 text-xs font-medium capitalize ${kind === k ? "bg-ink text-surface" : "text-mute"}`}
              >
                {k}
              </button>
            ))}
          </div>
          <select name="to_employee_id" required className="min-w-44 rounded-lg border border-line px-2 py-2 text-sm">
            <option value="">To…</option>
            {employees.map((e) => <option key={e.employee_id} value={e.employee_id}>{e.full_name}</option>)}
          </select>
          {kind === "recognition" && (
            <select name="badge" required className="rounded-lg border border-line px-2 py-2 text-sm capitalize">
              {badges.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          )}
          <span className="text-[11px] text-mute">
            {kind === "recognition" ? "Public on the wall" : "Private to the recipient"}
          </span>
        </div>
        <textarea name="message" required maxLength={1000} rows={2} placeholder="Say something specific…" className="w-full rounded-lg border border-line px-3 py-2 text-sm" />
        <button className="rounded-lg bg-ink px-4 py-1.5 text-sm font-medium text-surface">
          {kind === "recognition" ? "Post recognition" : "Send feedback"}
        </button>
      </form>

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
          Recognition wall <span className="font-normal text-mute">({wall.length})</span>
        </div>
        <div className="divide-y divide-line-2">
          {wall.length === 0 && <p className="px-4 py-3 text-sm text-mute">No recognition yet — be the first.</p>}
          {wall.map((f) => (
            <div key={f.id} className="flex gap-3 px-4 py-3">
              <Avatar name={f.to_name ?? "—"} size={32} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-ink">{f.to_name}</span>
                  {f.badge && (
                    <span className="rounded-full bg-green-soft px-2 py-0.5 text-[10px] font-semibold capitalize text-green-strong">
                      {f.badge}
                    </span>
                  )}
                  <span className="text-[10px] text-mute-2">from {f.from_name} · {timeAgo(f.created_at)}</span>
                </div>
                <p className="text-sm text-ink">{f.message}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">Received</div>
          <div className="divide-y divide-line-2">
            {received.length === 0 && <p className="px-4 py-3 text-sm text-mute">Nothing yet.</p>}
            {received.map((f) => <FeedbackRow key={f.id} f={f} dir="to" />)}
          </div>
        </section>
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">Given</div>
          <div className="divide-y divide-line-2">
            {given.length === 0 && <p className="px-4 py-3 text-sm text-mute">Nothing yet.</p>}
            {given.map((f) => <FeedbackRow key={f.id} f={f} dir="from" />)}
          </div>
        </section>
      </div>
    </div>
  );
}
