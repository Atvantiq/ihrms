"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createTenant,
  fetchAnnouncements,
  fetchPlans,
  fetchPlatformInsights,
  fetchStatutoryPacks,
  fetchTenants,
  postAnnouncement,
  retractAnnouncement,
  runBilling,
  setTenantStatus,
  type Announcement,
  type Plan,
  type PlatformInsights,
  type StatutoryPack,
  type Tenant,
} from "@/lib/api";

const LEVEL_STYLE: Record<Announcement["level"], string> = {
  info: "bg-blue-soft text-blue-strong",
  success: "bg-green-soft text-green-strong",
  warning: "bg-warn-soft text-warn-strong",
};

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

const STATUS_STYLE: Record<string, string> = {
  active: "bg-green-soft text-green-strong",
  trial: "bg-blue-soft text-blue-strong",
  suspended: "bg-warn-soft text-warn-strong",
  churned: "bg-red-soft text-red-strong",
};

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">{label}</div>
      <div className="text-2xl font-semibold text-ink">{value}</div>
      {hint && <div className="text-[10px] text-mute-2">{hint}</div>}
    </div>
  );
}

export default function ControlPlanePage() {
  const [insights, setInsights] = useState<PlatformInsights | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [packs, setPacks] = useState<StatutoryPack[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const reload = useCallback(() => {
    fetchPlatformInsights().then(setInsights).catch((e) => setError(e.message));
    fetchTenants().then(setTenants).catch((e) => setError(e.message));
    fetchAnnouncements().then(setAnnouncements).catch(() => {});
  }, []);

  useEffect(() => {
    reload();
    fetchPlans().then(setPlans).catch(() => {});
    fetchStatutoryPacks().then(setPacks).catch(() => {});
  }, [reload]);

  async function broadcast(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await postAnnouncement({
        title: fd.get("title") as string,
        body: fd.get("body") as string,
        level: fd.get("level") as string,
      });
      form.reset();
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function retract(id: string) {
    try {
      await retractAnnouncement(id);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await createTenant({
        id: fd.get("id") as string,
        name: fd.get("name") as string,
        plan_code: fd.get("plan_code") as string,
      });
      setShowAdd(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function status(t: Tenant, s: string) {
    try {
      await setTenantStatus(t.id, s);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function bill() {
    const now = new Date();
    try {
      const inv = await runBilling(now.getFullYear(), now.getMonth() + 1);
      const total = inv.reduce((s, i) => s + Number(i.amount), 0);
      setMsg(`Billed ${inv.length} tenant(s) · ${inr(total)} total`);
      setTimeout(() => setMsg(null), 3500);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Control Plane</h1>
          <p className="text-xs text-mute">
            Tenants · plans · billing (PEPM) · statutory rate master
          </p>
        </div>
        <div className="flex items-center gap-2">
          {msg && <span className="text-xs text-green-strong">{msg}</span>}
          <button onClick={bill} className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-mute hover:text-ink">
            Run billing
          </button>
          <button onClick={() => setShowAdd(!showAdd)} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
            + New tenant
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {insights && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Kpi label="Tenants" value={String(insights.tenants)} hint={`${insights.active_tenants} active`} />
          <Kpi label="MRR" value={inr(insights.mrr)} hint="recurring/mo" />
          <Kpi label="Billable employees" value={String(insights.billable_employees)} />
          <Kpi label="ARR (est.)" value={inr(Number(insights.mrr) * 12)} />
        </div>
      )}

      {showAdd && (
        <form onSubmit={add} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <input name="id" required placeholder="tenant-slug" pattern="[a-z0-9-]+" className="rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="name" required placeholder="Company name" className="flex-1 min-w-40 rounded-lg border border-line px-3 py-2 text-sm" />
          <select name="plan_code" required className="rounded-lg border border-line px-2 py-2 text-sm">
            {plans.map((p) => (
              <option key={p.code} value={p.code}>{p.name} ({inr(p.price_per_employee)}/emp)</option>
            ))}
          </select>
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Provision</button>
        </form>
      )}

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
          Tenants <span className="font-normal text-mute">({tenants.length})</span>
        </div>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">Tenant</th>
              <th className="px-3 py-2 font-semibold">Plan</th>
              <th className="px-3 py-2 font-semibold">Region</th>
              <th className="px-3 py-2 font-semibold">Employees</th>
              <th className="px-3 py-2 font-semibold">MRR</th>
              <th className="px-3 py-2 font-semibold">Status</th>
              <th className="px-3 py-2 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tenants.map((t) => (
              <tr key={t.id} className="border-b border-line-2 last:border-0">
                <td className="px-4 py-2">
                  <span className="block font-medium text-ink">{t.name}</span>
                  <span className="block font-mono text-[10px] text-mute">{t.id}</span>
                </td>
                <td className="px-3 py-2 capitalize text-mute">{t.plan_code}</td>
                <td className="px-3 py-2 font-mono text-xs text-mute">{t.region}</td>
                <td className="px-3 py-2 text-ink">{t.employee_count}</td>
                <td className="px-3 py-2 font-semibold text-ink">{inr(t.mrr)}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STATUS_STYLE[t.status]}`}>
                    {t.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-1.5">
                    {t.status !== "active" && (
                      <button onClick={() => status(t, "active")} className="rounded-md bg-green-soft px-2 py-1 text-[11px] font-medium text-green-strong">
                        Activate
                      </button>
                    )}
                    {t.status === "active" && (
                      <button onClick={() => status(t, "suspended")} className="rounded-md bg-warn-soft px-2 py-1 text-[11px] font-medium text-warn-strong">
                        Suspend
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">Plans</div>
          <div className="divide-y divide-line-2">
            {plans.map((p) => (
              <div key={p.code} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <span className="font-medium text-ink">{p.name}</span>
                <span className="text-mute">{inr(p.price_per_employee)}/employee · up to {p.included_employees}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
            Statutory rate master
          </div>
          <div className="divide-y divide-line-2">
            {packs.map((p) => (
              <div key={p.id} className="px-4 py-2.5 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink">{p.name}</span>
                  {p.is_active && (
                    <span className="rounded-full bg-green-soft px-2 py-0.5 text-[10px] font-medium text-green-strong">
                      active
                    </span>
                  )}
                </div>
                <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-mute">
                  <span>PF ceiling {inr(String(p.rates.pf_ceiling))}</span>
                  <span>ESI ≤ {inr(String(p.rates.esi_gross_ceiling))}</span>
                  <span>PT {inr(String(p.rates.pt_amount))}</span>
                  <span>cess {String(Number(p.rates.cess) * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
          Announcements <span className="font-normal text-mute">broadcast to every tenant&apos;s dashboard</span>
        </div>
        <form onSubmit={broadcast} className="flex flex-wrap items-end gap-3 border-b border-line-2 p-4">
          <input name="title" required maxLength={160} placeholder="Title" className="min-w-48 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="body" required maxLength={2000} placeholder="Message" className="min-w-64 flex-[2] rounded-lg border border-line px-3 py-2 text-sm" />
          <select name="level" defaultValue="info" className="rounded-lg border border-line px-2 py-2 text-sm">
            <option value="info">Info</option>
            <option value="success">Success</option>
            <option value="warning">Warning</option>
          </select>
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Broadcast</button>
        </form>
        <div className="divide-y divide-line-2">
          {announcements.length === 0 && (
            <p className="px-4 py-3 text-sm text-mute">No active announcements.</p>
          )}
          {announcements.map((a) => (
            <div key={a.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${LEVEL_STYLE[a.level]}`}>
                    {a.level}
                  </span>
                  <span className="font-medium text-ink">{a.title}</span>
                </div>
                <p className="mt-0.5 truncate text-xs text-mute">{a.body}</p>
              </div>
              <button onClick={() => retract(a.id)} className="shrink-0 rounded-md border border-line px-2 py-1 text-[11px] font-medium text-mute hover:text-red-strong">
                Retract
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
