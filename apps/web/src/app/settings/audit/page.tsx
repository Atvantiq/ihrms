"use client";

import { useEffect, useState } from "react";
import { fetchAuditEvents, type AuditEvent } from "@/lib/api";

const ENTITY_FILTERS = [
  { value: "", label: "All" },
  { value: "employee", label: "Employees" },
  { value: "leave_request", label: "Leave" },
  { value: "org_master", label: "Org masters" },
  { value: "holiday", label: "Holidays" },
];

const ACTION_STYLE: Record<string, string> = {
  create: "bg-green-soft text-green-strong",
  update: "bg-blue-soft text-blue-strong",
  approve: "bg-green-soft text-green-strong",
  reject: "bg-red-soft text-red-strong",
  cancel: "bg-line-2 text-mute",
  delete: "bg-red-soft text-red-strong",
  merge: "bg-warn-soft text-warn-strong",
  rename: "bg-blue-soft text-blue-strong",
};

function actionStyle(action: string): string {
  const verb = action.split(".")[1] ?? "";
  return ACTION_STYLE[verb] ?? "bg-line-2 text-mute";
}

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [entity, setEntity] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAuditEvents({ entity_type: entity, limit: 100 })
      .then(setEvents)
      .catch((e: Error) => setError(e.message));
  }, [entity]);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Audit log</h1>
          <p className="text-xs text-mute">
            Append-only record of every change — who, what, when.
          </p>
        </div>
        <select
          value={entity}
          onChange={(e) => setEntity(e.target.value)}
          className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"
        >
          {ENTITY_FILTERS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">When</th>
              <th className="px-3 py-2 font-semibold">Actor</th>
              <th className="px-3 py-2 font-semibold">Action</th>
              <th className="px-3 py-2 font-semibold">Detail</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id} className="border-b border-line-2 last:border-0">
                <td className="px-4 py-2 font-mono text-[11px] text-mute">
                  {new Date(e.created_at).toLocaleString()}
                </td>
                <td className="px-3 py-2 text-ink">{e.actor_email ?? "—"}</td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded-md px-1.5 py-0.5 font-mono text-[10px] ${actionStyle(e.action)}`}
                  >
                    {e.action}
                  </span>
                </td>
                <td className="px-3 py-2 text-mute">{e.summary ?? "—"}</td>
              </tr>
            ))}
            {events.length === 0 && !error && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-mute">
                  No audit events yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
