"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ackPolicy,
  fetchMe,
  fetchPolicies,
  fetchPolicyCompliance,
  publishPolicy,
  type Policy,
  type PolicyCompliance,
} from "@/lib/api";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [isHr, setIsHr] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [compliance, setCompliance] = useState<Record<string, PolicyCompliance>>({});
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchPolicies().then(setPolicies).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    reload();
    fetchMe().then((me) => setIsHr(me.is_hr));
  }, [reload]);

  async function publish(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await publishPolicy({
        title: fd.get("title") as string,
        category: (fd.get("category") as string) || "general",
        body: fd.get("body") as string,
        version: Number(fd.get("version") || 1),
      });
      form.reset();
      setShowAdd(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function ack(id: string) {
    try {
      await ackPolicy(id);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function loadCompliance(id: string) {
    try {
      setCompliance({ ...compliance, [id]: await fetchPolicyCompliance(id) });
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const pending = policies.filter((p) => !p.acknowledged).length;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Policies</h1>
          <p className="text-xs text-mute">
            {pending > 0 ? `${pending} awaiting your acknowledgement` : "All policies acknowledged"}
          </p>
        </div>
        {isHr && (
          <button onClick={() => setShowAdd(!showAdd)} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
            + Publish policy
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {showAdd && (
        <form onSubmit={publish} className="space-y-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="flex flex-wrap gap-3">
            <input name="title" required maxLength={160} placeholder="Title" className="min-w-44 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
            <input name="category" placeholder="Category" defaultValue="general" className="w-36 rounded-lg border border-line px-3 py-2 text-sm" />
            <input name="version" type="number" min="1" defaultValue="1" className="w-20 rounded-lg border border-line px-3 py-2 text-sm" />
          </div>
          <textarea name="body" required maxLength={20000} rows={4} placeholder="Policy text" className="w-full rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-1.5 text-sm font-medium text-surface">Publish</button>
        </form>
      )}

      {policies.length === 0 && (
        <div className="rounded-xl border border-line bg-surface p-8 text-center text-sm text-mute shadow-sm">
          No policies published.
        </div>
      )}

      {policies.map((p) => (
        <section key={p.id} className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <div>
              <span className="text-sm font-semibold text-ink">{p.title}</span>
              <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider text-mute">{p.category} · v{p.version}</span>
            </div>
            {p.acknowledged ? (
              <span className="rounded-full bg-green-soft px-2 py-0.5 text-[11px] font-medium text-green-strong">✓ acknowledged</span>
            ) : (
              <button onClick={() => ack(p.id)} className="rounded-md bg-ink px-3 py-1 text-[11px] font-medium text-surface hover:bg-ink-2">
                Acknowledge
              </button>
            )}
          </div>
          <div className="px-4 py-3">
            <p className="whitespace-pre-wrap text-sm text-ink">{p.body}</p>
            {isHr && (
              <div className="mt-2 text-[11px] text-mute">
                {compliance[p.id] ? (
                  <span>
                    Compliance: <span className="font-semibold text-ink">{compliance[p.id].acknowledged}</span> / {compliance[p.id].headcount} acknowledged · {compliance[p.id].pending} pending
                  </span>
                ) : (
                  <button onClick={() => loadCompliance(p.id)} className="text-indigo-strong hover:underline">
                    View compliance
                  </button>
                )}
              </div>
            )}
          </div>
        </section>
      ))}
    </div>
  );
}
