"use client";

import { useCallback, useEffect, useState } from "react";
import {
  downloadFile,
  fetchInsights,
  fetchReports,
  runReport,
  type Insights,
  type ReportData,
  type ReportMeta,
} from "@/lib/api";
import { ReportBuilder } from "@/components/ReportBuilder";

function KpiTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">{label}</div>
      <div className="text-2xl font-semibold text-ink">{value}</div>
      {hint && <div className="text-[10px] text-mute-2">{hint}</div>}
    </div>
  );
}

export default function ReportsPage() {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [reports, setReports] = useState<ReportMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [data, setData] = useState<ReportData | null>(null);
  const [tab, setTab] = useState<"prebuilt" | "builder">("prebuilt");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInsights().then(setInsights).catch((e) => setError(e.message));
    fetchReports().then(setReports).catch((e) => setError(e.message));
  }, []);

  const open = useCallback((id: string) => {
    setSelected(id);
    setData(null);
    runReport(id).then(setData).catch((e) => setError(e.message));
  }, []);

  function cell(v: unknown): string {
    if (v === null || v === undefined) return "—";
    return String(v);
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-ink">Reports &amp; Analytics</h1>
        <p className="text-xs text-mute">Cross-module insights and prebuilt reports · CSV export</p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <div className="flex gap-1 border-b border-line">
        {(["prebuilt", "builder"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium capitalize transition ${
              tab === t ? "border-b-2 border-ink text-ink" : "text-mute hover:text-ink"
            }`}
          >
            {t === "builder" ? "Custom builder" : "Prebuilt"}
          </button>
        ))}
      </div>

      {tab === "builder" && <ReportBuilder />}

      {tab === "prebuilt" && insights && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <KpiTile label="Headcount" value={String(insights.headcount)} hint="active" />
          <KpiTile label="Exits" value={String(insights.exits_total)} hint="completed F&F" />
          <KpiTile
            label="Monthly net"
            value={insights.latest_monthly_net ? "₹" + Number(insights.latest_monthly_net).toLocaleString("en-IN") : "—"}
            hint="latest run"
          />
          <KpiTile
            label="Avg tenure"
            value={insights.avg_tenure_months ? `${insights.avg_tenure_months}m` : "—"}
          />
          <KpiTile label="Open reqs" value={String(insights.open_requisitions)} hint="hiring" />
        </div>
      )}

      {tab === "prebuilt" && (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
            Reports
          </div>
          <div className="divide-y divide-line-2">
            {reports.map((r) => (
              <button
                key={r.id}
                onClick={() => open(r.id)}
                className={`w-full px-4 py-2.5 text-left hover:bg-line-2/50 ${selected === r.id ? "bg-indigo-soft/40" : ""}`}
              >
                <span className="block text-sm font-medium text-ink">{r.name}</span>
                <span className="block text-[10px] text-mute">{r.description}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-line bg-surface shadow-sm lg:col-span-2">
          {data ? (
            <>
              <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
                <span className="text-sm font-semibold text-ink">
                  {data.name} <span className="font-normal text-mute">({data.rows.length})</span>
                </span>
                <button
                  onClick={() => downloadFile(`/reports/${data.id}/csv`, `${data.id}.csv`)}
                  className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-mute hover:text-ink"
                >
                  ⬇ CSV
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
                      {data.columns.map((c) => (
                        <th key={c} className="px-4 py-2 font-semibold">{c.replace(/_/g, " ")}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((row, i) => (
                      <tr key={i} className="border-b border-line-2 last:border-0">
                        {data.columns.map((c) => (
                          <td key={c} className="px-4 py-2 text-ink">{cell(row[c])}</td>
                        ))}
                      </tr>
                    ))}
                    {data.rows.length === 0 && (
                      <tr>
                        <td colSpan={data.columns.length} className="px-4 py-6 text-center text-mute">
                          No data.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="flex h-40 items-center justify-center text-sm text-mute">
              {selected ? "Loading…" : "Pick a report to view."}
            </div>
          )}
        </section>
      </div>
      )}
    </div>
  );
}
