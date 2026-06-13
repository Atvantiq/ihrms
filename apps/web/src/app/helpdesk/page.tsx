"use client";

import { useCallback, useEffect, useState } from "react";
import {
  assignTicket,
  fetchMe,
  fetchTicketCategories,
  fetchTickets,
  raiseTicket,
  setTicketStatus,
  type Ticket,
} from "@/lib/api";

const STATUS_STYLE: Record<Ticket["status"], string> = {
  open: "bg-warn-soft text-warn-strong",
  in_progress: "bg-blue-soft text-blue-strong",
  resolved: "bg-green-soft text-green-strong",
  closed: "bg-line-2 text-mute",
};
const PRIORITY_STYLE: Record<string, string> = {
  high: "text-red-strong",
  medium: "text-warn-strong",
  low: "text-mute",
};

export default function HelpdeskPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [isHr, setIsHr] = useState(false);
  const [view, setView] = useState<"mine" | "all">("mine");
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback((scope: "mine" | "all") => {
    fetchTickets(scope).then(setTickets).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    fetchTicketCategories().then(setCategories).catch(() => {});
    fetchMe().then((me) => setIsHr(me.is_hr));
  }, []);
  useEffect(() => reload(view), [reload, view]);

  async function raise(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await raiseTicket({
        category: fd.get("category") as string,
        subject: fd.get("subject") as string,
        description: fd.get("description") as string,
        priority: fd.get("priority") as string,
      });
      form.reset();
      reload(view);
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function progress(t: Ticket, status: string) {
    try {
      const resolution = status === "resolved" ? prompt("Resolution note?") || undefined : undefined;
      await setTicketStatus(t.id, status, resolution);
      reload(view);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function claim(t: Ticket) {
    try {
      const me = await fetchMe();
      await assignTicket(t.id, me.employee_id);
      reload(view);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Helpdesk</h1>
          <p className="text-xs text-mute">Raise a request — payroll, leave, IT, facilities, HR</p>
        </div>
        {isHr && (
          <div className="flex gap-1 rounded-lg border border-line p-0.5">
            {(["mine", "all"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)} className={`rounded-md px-3 py-1 text-xs font-medium capitalize ${view === v ? "bg-ink text-surface" : "text-mute"}`}>
                {v === "mine" ? "My tickets" : "All tickets"}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <form onSubmit={raise} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
        <select name="category" className="rounded-lg border border-line px-2 py-2 text-sm capitalize">
          {categories.map((c) => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
        </select>
        <select name="priority" defaultValue="medium" className="rounded-lg border border-line px-2 py-2 text-sm">
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <input name="subject" required maxLength={160} placeholder="Subject" className="min-w-40 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
        <input name="description" required maxLength={2000} placeholder="Describe the issue" className="min-w-48 flex-[2] rounded-lg border border-line px-3 py-2 text-sm" />
        <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Raise</button>
      </form>

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="divide-y divide-line-2">
          {tickets.length === 0 && <p className="px-4 py-6 text-center text-sm text-mute">No tickets.</p>}
          {tickets.map((t) => (
            <div key={t.id} className="px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="min-w-0">
                  <span className="text-sm font-medium text-ink">{t.subject}</span>
                  <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-mute">{t.category.replace("_", " ")}</span>
                  <span className={`ml-2 text-[10px] font-semibold uppercase ${PRIORITY_STYLE[t.priority]}`}>{t.priority}</span>
                </span>
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLE[t.status]}`}>
                  {t.status.replace("_", " ")}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-mute">{t.description}</p>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-[10px] text-mute-2">
                  {view === "all" ? `by ${t.employee_name} · ` : ""}
                  {t.assignee_name ? `assigned to ${t.assignee_name}` : "unassigned"}
                  {t.resolution ? ` · ${t.resolution}` : ""}
                </span>
                {isHr && t.status !== "closed" && t.status !== "resolved" && (
                  <span className="flex gap-1.5">
                    {!t.assignee_id && (
                      <button onClick={() => claim(t)} className="rounded-md border border-line px-2 py-0.5 text-[10px] text-mute hover:text-ink">
                        Claim
                      </button>
                    )}
                    <button onClick={() => progress(t, "resolved")} className="rounded-md bg-green-soft px-2 py-0.5 text-[10px] font-medium text-green-strong">
                      Resolve
                    </button>
                    <button onClick={() => progress(t, "closed")} className="rounded-md border border-line px-2 py-0.5 text-[10px] text-mute hover:text-ink">
                      Close
                    </button>
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
