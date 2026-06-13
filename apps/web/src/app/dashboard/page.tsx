"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchDashboard, type DashboardSummary } from "@/lib/api";
import { Avatar } from "@/components/Avatar";

function StatTile({
  label,
  value,
  hint,
  valueClass,
}: {
  label: string;
  value: number;
  hint: string;
  valueClass: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">
        {label}
      </div>
      <div className={`text-2xl font-semibold ${valueClass}`}>{value}</div>
      <div className="text-[10px] text-mute-2">{hint}</div>
    </div>
  );
}

function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 space-y-5 p-6">
      <div>
        <h1 className="text-xl font-semibold text-ink">Dashboard</h1>
        <p className="text-xs text-mute">Your organisation at a glance</p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatTile label="Headcount" value={data.headcount.total} hint="all employees" valueClass="text-ink" />
            <StatTile label="Active" value={data.headcount.active} hint="past probation" valueClass="text-green" />
            <StatTile label="Probation" value={data.headcount.probation} hint="first 90 days" valueClass="text-warn" />
            <StatTile label="On notice" value={data.headcount.notice} hint="serving" valueClass="text-warn" />
            <StatTile label="Inactive" value={data.headcount.inactive} hint="left · disabled" valueClass="text-mute" />
            <StatTile label="On leave today" value={data.on_leave_today.length} hint="approved" valueClass="text-indigo" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Panel
              title="Pending leave approvals"
              action={
                <Link href="/leave" className="text-xs text-indigo-strong hover:underline">
                  Review →
                </Link>
              }
            >
              {data.my_pending_approvals > 0 ? (
                <div className="flex items-center gap-3">
                  <div className="text-3xl font-semibold text-warn">
                    {data.my_pending_approvals}
                  </div>
                  <div className="text-sm text-mute">
                    request{data.my_pending_approvals === 1 ? "" : "s"} awaiting your
                    decision
                  </div>
                </div>
              ) : (
                <p className="text-sm text-mute">Nothing awaiting approval. 🎉</p>
              )}
            </Panel>

            <Panel title="On leave today">
              {data.on_leave_today.length > 0 ? (
                <ul className="space-y-2">
                  {data.on_leave_today.map((l, i) => (
                    <li key={i} className="flex items-center gap-2.5 text-sm">
                      <Avatar name={l.employee_name} size={26} />
                      <span className="flex-1 text-ink">{l.employee_name}</span>
                      <span className="rounded bg-line-2 px-1.5 py-0.5 font-mono text-[10px] text-mute">
                        {l.leave_code}
                      </span>
                      <span className="text-[11px] text-mute-2">until {l.end_date}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-mute">Everyone&apos;s in today.</p>
              )}
            </Panel>

            <Panel
              title="New joiners"
              action={
                <Link href="/directory" className="text-xs text-indigo-strong hover:underline">
                  Directory →
                </Link>
              }
            >
              {data.new_joiners.length > 0 ? (
                <ul className="space-y-2">
                  {data.new_joiners.map((j, i) => (
                    <li key={i} className="flex items-center gap-2.5 text-sm">
                      <Avatar name={j.full_name} size={26} />
                      <span className="flex-1">
                        <span className="text-ink">{j.full_name}</span>
                        <span className="block text-[10px] text-mute">
                          {j.designation ?? "—"}
                        </span>
                      </span>
                      <span className="text-[11px] text-mute-2">{j.date_of_joining}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-mute">No recent joiners.</p>
              )}
            </Panel>

            <Panel
              title="Upcoming holidays"
              action={
                <Link
                  href="/settings/holidays"
                  className="text-xs text-indigo-strong hover:underline"
                >
                  Calendar →
                </Link>
              }
            >
              {data.upcoming_holidays.length > 0 ? (
                <ul className="space-y-2">
                  {data.upcoming_holidays.map((h, i) => (
                    <li key={i} className="flex items-center justify-between text-sm">
                      <span className="text-ink">{h.name}</span>
                      <span className="font-mono text-[11px] text-mute">
                        {h.holiday_date}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-mute">No upcoming holidays.</p>
              )}
            </Panel>
          </div>
        </>
      )}
    </main>
  );
}
