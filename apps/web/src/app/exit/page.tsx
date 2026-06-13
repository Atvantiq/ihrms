"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addKt,
  approveFnf,
  clearItem,
  computeFnf,
  downloadFile,
  fetchAlumni,
  fetchEmployeeAssets,
  fetchEmployees,
  fetchExitAnalytics,
  fetchExitCases,
  fetchInterview,
  fetchKt,
  initiateExit,
  payFnf,
  returnAsset,
  saveInterview,
  seedKt,
  toggleKt,
  upsertAlumni,
  type Alumnus,
  type Asset,
  type EmployeeListItem,
  type ExitAnalytics,
  type ExitCase,
  type ExitInterview,
  type KtItem,
} from "@/lib/api";

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

const STATUS_STYLE: Record<string, string> = {
  initiated: "bg-line-2 text-mute",
  clearance: "bg-blue-soft text-blue-strong",
  fnf_computed: "bg-warn-soft text-warn-strong",
  approved: "bg-indigo-soft text-indigo-strong",
  paid: "bg-green-soft text-green-strong",
};

function CaseCard({ c, onChanged, onError }: { c: ExitCase; onChanged: () => void; onError: (m: string) => void }) {
  const [assets, setAssets] = useState<Asset[]>([]);

  const loadAssets = useCallback(() => {
    fetchEmployeeAssets(c.employee_id).then(setAssets).catch(() => {});
  }, [c.employee_id]);
  useEffect(() => loadAssets(), [loadAssets]);

  async function act(fn: () => Promise<unknown>) {
    try {
      await fn();
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function recover(assetId: string) {
    try {
      await returnAsset(assetId);
      loadAssets();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  const allCleared = c.clearance.every((i) => i.status === "cleared");

  return (
    <section className="rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <div>
          <span className="text-sm font-semibold text-ink">{c.employee_name}</span>
          <span className="ml-2 text-[10px] text-mute">
            resigned {c.resignation_date} · LWD {c.last_working_day}
          </span>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLE[c.status]}`}>
          {c.status.replace("_", " ")}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-mute">
            Clearance
          </div>
          <div className="space-y-1.5">
            {c.clearance.map((i) => (
              <div key={i.id} className="flex items-center justify-between text-sm">
                <span className={i.status === "cleared" ? "text-mute line-through" : "text-ink"}>
                  {i.item}
                </span>
                {i.status === "cleared" ? (
                  <span className="text-green-strong">✓</span>
                ) : (
                  <button onClick={() => act(() => clearItem(c.id, i.id))} className="rounded-md border border-line px-2 py-0.5 text-[10px] text-mute hover:text-ink">
                    Clear
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-mute">
            Full &amp; Final
          </div>
          {c.fnf ? (
            <div className="space-y-1 text-sm">
              <Row label="Pending salary" v={c.fnf.pending_salary} />
              <Row label="Gratuity" v={c.fnf.gratuity} />
              <Row label="Leave encashment" v={c.fnf.leave_encashment} />
              <Row label="Notice recovery" v={c.fnf.notice_recovery} neg />
              <Row label="Other recoveries" v={c.fnf.other_recoveries} neg />
              <div className="mt-1 flex justify-between border-t border-line pt-1 font-semibold text-ink">
                <span>Net settlement</span>
                <span>{inr(c.fnf.net_settlement)}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-mute">Not computed yet.</p>
          )}
        </div>
      </div>

      {assets.length > 0 && (
        <div className="border-t border-line px-4 py-3">
          <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-mute">
            Assets to recover
            <span className="rounded-full bg-warn-soft px-1.5 py-0.5 text-[9px] text-warn-strong">
              {assets.length} outstanding
            </span>
          </div>
          <div className="space-y-1.5">
            {assets.map((a) => (
              <div key={a.id} className="flex items-center justify-between text-sm">
                <span className="text-ink">
                  {a.name}
                  <span className="ml-2 font-mono text-[10px] text-mute">{a.asset_tag}</span>
                </span>
                <button
                  onClick={() => recover(a.id)}
                  className="rounded-md border border-line px-2 py-0.5 text-[10px] text-mute hover:text-ink"
                >
                  Mark returned
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <KtInterviewPanel caseId={c.id} onError={onError} />

      <div className="flex flex-wrap justify-end gap-2 border-t border-line px-4 py-2.5">
        {c.status === "clearance" && (
          <button onClick={() => act(() => computeFnf(c.id))} className="rounded-lg bg-warn-soft px-3 py-1.5 text-xs font-medium text-warn-strong">
            Compute F&amp;F
          </button>
        )}
        {c.status === "fnf_computed" && (
          <button
            onClick={() => act(() => approveFnf(c.id))}
            disabled={!allCleared}
            title={allCleared ? "" : "Clear all items first"}
            className="rounded-lg bg-indigo-soft px-3 py-1.5 text-xs font-medium text-indigo-strong disabled:opacity-50"
          >
            Approve F&amp;F
          </button>
        )}
        {c.status === "approved" && (
          <button onClick={() => act(() => payFnf(c.id))} className="rounded-lg bg-green-soft px-3 py-1.5 text-xs font-medium text-green-strong">
            Pay &amp; revoke access
          </button>
        )}
        {c.status === "paid" && (
          <button
            onClick={() => downloadFile(`/exit/cases/${c.id}/relieving-letter`, `relieving_${c.employee_id}.pdf`)}
            className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-mute hover:text-ink"
          >
            Relieving letter
          </button>
        )}
      </div>
    </section>
  );
}

function Row({ label, v, neg }: { label: string; v: string; neg?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-mute">{label}</span>
      <span className={neg && Number(v) > 0 ? "text-red-strong" : "text-ink"}>
        {neg && Number(v) > 0 ? "−" : ""}
        {inr(v)}
      </span>
    </div>
  );
}

function KtInterviewPanel({ caseId, onError }: { caseId: string; onError: (m: string) => void }) {
  const [open, setOpen] = useState(false);
  const [kt, setKt] = useState<KtItem[]>([]);
  const [interview, setInterview] = useState<ExitInterview | null>(null);
  const [editIv, setEditIv] = useState(false);

  const load = useCallback(() => {
    fetchKt(caseId).then(setKt).catch(() => {});
    fetchInterview(caseId).then(setInterview).catch(() => {});
  }, [caseId]);
  useEffect(() => {
    if (open) load();
  }, [open, load]);

  async function act(fn: () => Promise<unknown>) {
    try {
      await fn();
      load();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  const ktDone = kt.filter((i) => i.status === "done").length;

  return (
    <div className="border-t border-line">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-mute hover:text-ink"
      >
        <span>Knowledge transfer &amp; exit interview</span>
        <span className="text-[11px] normal-case">
          {open ? "▾" : "▸"} KT {ktDone}/{kt.length}
          {interview ? " · interview ✓" : ""}
        </span>
      </button>

      {open && (
        <div className="grid grid-cols-1 gap-4 px-4 pb-4 lg:grid-cols-2">
          {/* KT checklist */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-mute">
                KT checklist
              </span>
              {kt.length === 0 && (
                <button
                  onClick={() => act(() => seedKt(caseId))}
                  className="text-[11px] text-blue-strong hover:underline"
                >
                  Seed defaults
                </button>
              )}
            </div>
            <div className="space-y-1.5">
              {kt.map((i) => (
                <label key={i.id} className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={i.status === "done"}
                    onChange={() => act(() => toggleKt(caseId, i.id))}
                  />
                  <span className={i.status === "done" ? "text-mute line-through" : "text-ink"}>
                    {i.task}
                  </span>
                  {i.assignee && <span className="text-[10px] text-mute-2">· {i.assignee}</span>}
                </label>
              ))}
              {kt.length === 0 && <p className="text-xs text-mute">No KT tasks yet.</p>}
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                const t = (fd.get("task") as string).trim();
                if (t) act(() => addKt(caseId, t, (fd.get("assignee") as string) || undefined));
                e.currentTarget.reset();
              }}
              className="mt-2 flex gap-2"
            >
              <input name="task" placeholder="Add KT task" className="flex-1 rounded-lg border border-line px-2 py-1 text-xs" />
              <input name="assignee" placeholder="Owner" className="w-24 rounded-lg border border-line px-2 py-1 text-xs" />
              <button className="rounded-lg border border-line px-2 py-1 text-xs text-mute hover:text-ink">Add</button>
            </form>
          </div>

          {/* Exit interview */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-mute">
                Exit interview
              </span>
              {!editIv && (
                <button
                  onClick={() => setEditIv(true)}
                  className="text-[11px] text-blue-strong hover:underline"
                >
                  {interview ? "Edit" : "Record"}
                </button>
              )}
            </div>
            {editIv ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const fd = new FormData(e.currentTarget);
                  act(() =>
                    saveInterview(caseId, {
                      primary_reason: (fd.get("primary_reason") as string) || null,
                      would_recommend: fd.get("would_recommend") === "yes",
                      rating_management: Number(fd.get("rating_management")) || null,
                      rating_role: Number(fd.get("rating_role")) || null,
                      rating_culture: Number(fd.get("rating_culture")) || null,
                      feedback: (fd.get("feedback") as string) || null,
                    }),
                  ).then(() => setEditIv(false));
                }}
                className="space-y-2 text-sm"
              >
                <input name="primary_reason" defaultValue={interview?.primary_reason ?? ""} placeholder="Primary reason" className="w-full rounded-lg border border-line px-2 py-1 text-xs" />
                <div className="flex gap-2">
                  {(["management", "role", "culture"] as const).map((k) => (
                    <label key={k} className="flex-1 text-[10px] uppercase text-mute">
                      {k}
                      <input
                        name={`rating_${k}`}
                        type="number"
                        min="1"
                        max="5"
                        defaultValue={interview?.[`rating_${k}` as keyof ExitInterview] as number ?? ""}
                        className="mt-0.5 block w-full rounded-lg border border-line px-2 py-1 text-xs"
                      />
                    </label>
                  ))}
                </div>
                <label className="flex items-center gap-2 text-xs text-mute">
                  <input name="would_recommend" type="checkbox" value="yes" defaultChecked={interview?.would_recommend === true} />
                  Would recommend as employer
                </label>
                <textarea name="feedback" defaultValue={interview?.feedback ?? ""} placeholder="Feedback" rows={2} className="w-full rounded-lg border border-line px-2 py-1 text-xs" />
                <div className="flex gap-2">
                  <button className="rounded-lg bg-ink px-3 py-1 text-xs font-medium text-surface">Save</button>
                  <button type="button" onClick={() => setEditIv(false)} className="text-xs text-mute">cancel</button>
                </div>
              </form>
            ) : interview ? (
              <div className="space-y-1 text-sm">
                <div className="text-ink">{interview.primary_reason ?? "—"}</div>
                <div className="text-[11px] text-mute">
                  Mgmt {interview.rating_management ?? "—"}/5 · Role {interview.rating_role ?? "—"}/5 ·
                  Culture {interview.rating_culture ?? "—"}/5
                </div>
                <div className="text-[11px]">
                  {interview.would_recommend == null ? (
                    <span className="text-mute">recommend: —</span>
                  ) : interview.would_recommend ? (
                    <span className="text-green-strong">would recommend ✓</span>
                  ) : (
                    <span className="text-red-strong">would not recommend</span>
                  )}
                </div>
                {interview.feedback && <p className="text-[11px] text-mute">“{interview.feedback}”</p>}
              </div>
            ) : (
              <p className="text-xs text-mute">No interview recorded.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function AlumniView({ onError }: { onError: (m: string) => void }) {
  const [rows, setRows] = useState<Alumnus[]>([]);
  const load = useCallback(() => {
    fetchAlumni().then(setRows).catch((e) => onError((e as Error).message));
  }, [onError]);
  useEffect(() => load(), [load]);

  async function toggle(a: Alumnus) {
    try {
      await upsertAlumni({ employee_id: a.employee_id, eligible_for_rehire: !a.eligible_for_rehire });
      load();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
        Alumni &amp; rehire register <span className="font-normal text-mute">({rows.length})</span>
      </div>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
            <th className="px-4 py-2 font-semibold">Alumnus</th>
            <th className="px-3 py-2 font-semibold">Left</th>
            <th className="px-3 py-2 font-semibold">Contact</th>
            <th className="px-3 py-2 font-semibold">Rehire</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => (
            <tr key={a.id} className="border-b border-line-2 last:border-0">
              <td className="px-4 py-2 text-ink">
                {a.employee_name}
                {a.note && <span className="ml-2 text-[11px] text-mute">{a.note}</span>}
              </td>
              <td className="px-3 py-2 text-[11px] text-mute">{a.last_working_day ?? "—"}</td>
              <td className="px-3 py-2 text-[11px] text-mute">{a.personal_email ?? "—"}</td>
              <td className="px-3 py-2">
                <button
                  onClick={() => toggle(a)}
                  className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                    a.eligible_for_rehire
                      ? "bg-green-soft text-green-strong"
                      : "bg-red-soft text-red-strong"
                  }`}
                >
                  {a.eligible_for_rehire ? "eligible" : "not eligible"}
                </button>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="px-4 py-8 text-center text-sm text-mute">
                No alumni recorded yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

function AnalyticsView({ onError }: { onError: (m: string) => void }) {
  const [a, setA] = useState<ExitAnalytics | null>(null);
  useEffect(() => {
    fetchExitAnalytics().then(setA).catch((e) => onError((e as Error).message));
  }, [onError]);
  if (!a) return null;

  const maxReason = Math.max(1, ...Object.values(a.by_reason));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Total exits" value={String(a.total_exits)} />
        <Stat label="Attrition" value={`${a.attrition_rate_pct}%`} accent="text-warn-strong" />
        <Stat label="Avg tenure" value={`${(a.avg_tenure_days / 365).toFixed(1)}y`} />
        <Stat label="Reasons" value={String(Object.keys(a.by_reason).length)} />
      </div>
      <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-ink">Exits by reason</h2>
        <div className="space-y-2">
          {Object.entries(a.by_reason).map(([reason, n]) => (
            <div key={reason} className="flex items-center gap-3 text-sm">
              <span className="w-44 shrink-0 truncate text-mute">{reason}</span>
              <div className="h-4 flex-1 rounded bg-line-2">
                <div
                  className="h-4 rounded bg-indigo"
                  style={{ width: `${(n / maxReason) * 100}%` }}
                />
              </div>
              <span className="w-6 text-right font-mono text-ink">{n}</span>
            </div>
          ))}
          {Object.keys(a.by_reason).length === 0 && (
            <p className="text-sm text-mute">No exit data yet.</p>
          )}
        </div>
      </section>
      {Object.keys(a.by_month).length > 0 && (
        <section className="rounded-xl border border-line bg-surface p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-ink">Exits by month</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(a.by_month).map(([m, n]) => (
              <span key={m} className="rounded-lg border border-line px-2 py-1 text-[11px] text-mute">
                {m} <span className="font-semibold text-ink">{n}</span>
              </span>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">{label}</div>
      <div className={`text-2xl font-semibold ${accent ?? "text-ink"}`}>{value}</div>
    </div>
  );
}

type ExitTab = "cases" | "alumni" | "analytics";

export default function ExitPage() {
  const [cases, setCases] = useState<ExitCase[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [show, setShow] = useState(false);
  const [tab, setTab] = useState<ExitTab>("cases");
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchExitCases().then(setCases).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    reload();
    fetchEmployees({ status: "Active" }).then((d) => setEmployees(d.items)).catch(() => {});
  }, [reload]);

  async function initiate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await initiateExit({
        employee_id: Number(fd.get("employee_id")),
        resignation_date: fd.get("resignation_date") as string,
        last_working_day: fd.get("last_working_day") as string,
        reason: (fd.get("reason") as string) || undefined,
        notice_required_days: Number(fd.get("notice")) || 60,
      });
      setShow(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Exit &amp; Full-and-Final</h1>
          <p className="text-xs text-mute">
            Resignation → clearance → F&amp;F → pay → access revoked
          </p>
        </div>
        <button onClick={() => setShow(!show)} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
          + Initiate exit
        </button>
      </div>

      <div className="flex gap-1 border-b border-line">
        {(["cases", "alumni", "analytics"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium capitalize transition ${
              tab === t ? "border-b-2 border-ink text-ink" : "text-mute hover:text-ink"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {tab === "alumni" && <AlumniView onError={setError} />}
      {tab === "analytics" && <AnalyticsView onError={setError} />}

      {tab === "cases" && show && (
        <form onSubmit={initiate} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-mute">Employee</label>
            <select name="employee_id" required className="rounded-lg border border-line px-2 py-2 text-sm">
              <option value="">Select…</option>
              {employees.map((m) => (
                <option key={m.employee_id} value={m.employee_id}>{m.full_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-mute">Resignation date</label>
            <input name="resignation_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-mute">Last working day</label>
            <input name="last_working_day" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-mute">Notice (days)</label>
            <input name="notice" type="number" defaultValue={60} className="w-20 rounded-lg border border-line px-2 py-2 text-sm" />
          </div>
          <input name="reason" placeholder="Reason" className="flex-1 min-w-40 rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Initiate</button>
        </form>
      )}

      {tab === "cases" && (
        <div className="space-y-4">
          {cases.map((c) => (
            <CaseCard key={c.id} c={c} onChanged={reload} onError={setError} />
          ))}
          {cases.length === 0 && (
            <div className="rounded-xl border border-line bg-surface p-8 text-center text-sm text-mute shadow-sm">
              No exit cases.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
