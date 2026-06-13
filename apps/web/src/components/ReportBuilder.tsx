"use client";

import { useEffect, useMemo, useState } from "react";
import {
  buildReport,
  fetchDatasets,
  type DatasetMeta,
  type ReportData,
} from "@/lib/api";

const OP_LABEL: Record<string, string> = {
  eq: "is",
  ne: "is not",
  gt: ">",
  gte: "≥",
  lt: "<",
  lte: "≤",
  contains: "contains",
};

interface FilterRow {
  field: string;
  op: string;
  value: string;
}

function toCsv(columns: string[], rows: Record<string, unknown>[]): string {
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [columns.join(","), ...rows.map((r) => columns.map((c) => esc(r[c])).join(","))].join("\n");
}

export function ReportBuilder() {
  const [datasets, setDatasets] = useState<DatasetMeta[]>([]);
  const [dsKey, setDsKey] = useState("");
  const [cols, setCols] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterRow[]>([]);
  const [data, setData] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDatasets()
      .then((d) => {
        setDatasets(d);
        if (d[0]) selectDataset(d[0]);
      })
      .catch((e) => setError(e.message));
  }, []);

  const ds = useMemo(() => datasets.find((d) => d.key === dsKey), [datasets, dsKey]);

  function selectDataset(d: DatasetMeta) {
    setDsKey(d.key);
    setCols(d.columns.map((c) => c.key));
    setFilters([]);
    setData(null);
  }

  function toggleCol(key: string) {
    setCols((prev) => (prev.includes(key) ? prev.filter((c) => c !== key) : [...prev, key]));
  }

  function addFilter() {
    if (!ds || ds.filters.length === 0) return;
    const f = ds.filters[0];
    setFilters((prev) => [...prev, { field: f.key, op: f.ops[0], value: "" }]);
  }

  function updateFilter(i: number, patch: Partial<FilterRow>) {
    setFilters((prev) => prev.map((f, idx) => (idx === i ? { ...f, ...patch } : f)));
  }

  async function run() {
    if (!ds) return;
    try {
      const result = await buildReport({
        dataset: ds.key,
        columns: cols,
        filters: filters.filter((f) => f.value !== "" || f.op === "eq"),
      });
      setData(result);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function download() {
    if (!data) return;
    const blob = new Blob([toCsv(data.columns, data.rows)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.id}_custom.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <section className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
            Dataset
            <select
              value={dsKey}
              onChange={(e) => {
                const d = datasets.find((x) => x.key === e.target.value);
                if (d) selectDataset(d);
              }}
              className="ml-2 rounded-lg border border-line px-2 py-1.5 text-sm font-normal normal-case text-ink"
            >
              {datasets.map((d) => (
                <option key={d.key} value={d.key}>{d.name}</option>
              ))}
            </select>
          </label>
          <button onClick={run} className="ml-auto rounded-lg bg-ink px-4 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
            Run report
          </button>
        </div>

        {ds && (
          <>
            <div className="mt-3">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-mute">Columns</div>
              <div className="flex flex-wrap gap-2">
                {ds.columns.map((c) => (
                  <button
                    key={c.key}
                    onClick={() => toggleCol(c.key)}
                    className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                      cols.includes(c.key)
                        ? "bg-indigo-soft text-indigo-strong"
                        : "bg-line-2 text-mute"
                    }`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-3">
              <div className="mb-1 flex items-center gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-mute">Filters</span>
                {ds.filters.length > 0 && (
                  <button onClick={addFilter} className="text-[11px] text-blue-strong hover:underline">
                    + add filter
                  </button>
                )}
              </div>
              <div className="space-y-2">
                {filters.map((f, i) => {
                  const fld = ds.filters.find((x) => x.key === f.field);
                  return (
                    <div key={i} className="flex flex-wrap items-center gap-2 text-sm">
                      <select
                        value={f.field}
                        onChange={(e) => {
                          const nf = ds.filters.find((x) => x.key === e.target.value)!;
                          updateFilter(i, { field: nf.key, op: nf.ops[0] });
                        }}
                        className="rounded-lg border border-line px-2 py-1 text-xs"
                      >
                        {ds.filters.map((x) => (
                          <option key={x.key} value={x.key}>{x.label}</option>
                        ))}
                      </select>
                      <select
                        value={f.op}
                        onChange={(e) => updateFilter(i, { op: e.target.value })}
                        className="rounded-lg border border-line px-2 py-1 text-xs"
                      >
                        {(fld?.ops ?? []).map((op) => (
                          <option key={op} value={op}>{OP_LABEL[op] ?? op}</option>
                        ))}
                      </select>
                      <input
                        value={f.value}
                        onChange={(e) => updateFilter(i, { value: e.target.value })}
                        placeholder="value"
                        className="rounded-lg border border-line px-2 py-1 text-xs"
                      />
                      <button
                        onClick={() => setFilters((prev) => prev.filter((_, idx) => idx !== i))}
                        className="text-[11px] text-mute hover:text-red-strong"
                      >
                        remove
                      </button>
                    </div>
                  );
                })}
                {filters.length === 0 && <p className="text-[11px] text-mute-2">No filters — returns all rows.</p>}
              </div>
            </div>
          </>
        )}
      </section>

      {data && (
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <span className="text-sm font-semibold text-ink">
              {data.name} <span className="font-normal text-mute">({data.rows.length})</span>
            </span>
            <button onClick={download} className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-mute hover:text-ink">
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
                      <td key={c} className="px-4 py-2 text-ink">
                        {row[c] === null || row[c] === undefined ? "—" : String(row[c])}
                      </td>
                    ))}
                  </tr>
                ))}
                {data.rows.length === 0 && (
                  <tr>
                    <td colSpan={data.columns.length} className="px-4 py-6 text-center text-mute">
                      No rows match.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
