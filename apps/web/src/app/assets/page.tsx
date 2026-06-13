"use client";

import { useCallback, useEffect, useState } from "react";
import {
  assignAsset,
  createAsset,
  fetchAssets,
  fetchDepreciation,
  fetchEmployees,
  returnAsset,
  type Asset,
  type DepreciationReport,
  type EmployeeListItem,
} from "@/lib/api";

const STATUS_STYLE: Record<Asset["status"], string> = {
  in_stock: "bg-green-soft text-green-strong",
  assigned: "bg-blue-soft text-blue-strong",
  retired: "bg-line-2 text-mute",
  lost: "bg-red-soft text-red-strong",
};

const CATEGORIES = ["laptop", "desktop", "phone", "monitor", "peripheral", "furniture", "other"];

function inr(v: string | number | null): string {
  if (v === null) return "—";
  return "₹" + Number(v).toLocaleString("en-IN");
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [assigning, setAssigning] = useState<string | null>(null);
  const [dep, setDep] = useState<DepreciationReport | null>(null);
  const [showDep, setShowDep] = useState(false);

  const reload = useCallback(() => {
    fetchAssets().then(setAssets).catch((e) => setError(e.message));
    fetchDepreciation().then(setDep).catch(() => {});
  }, []);

  useEffect(() => {
    reload();
    fetchEmployees({ limit: 500 })
      .then((r) => setEmployees(r.items))
      .catch(() => {});
  }, [reload]);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await createAsset({
        asset_tag: fd.get("asset_tag") as string,
        category: fd.get("category") as string,
        name: fd.get("name") as string,
        serial_no: (fd.get("serial_no") as string) || null,
        purchase_date: (fd.get("purchase_date") as string) || null,
        purchase_cost: (fd.get("purchase_cost") as string) || null,
      });
      form.reset();
      setShowAdd(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function assign(assetId: string, employeeId: number) {
    try {
      await assignAsset(assetId, employeeId);
      setAssigning(null);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function doReturn(assetId: string) {
    try {
      await returnAsset(assetId);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const inStock = assets.filter((a) => a.status === "in_stock").length;
  const assigned = assets.filter((a) => a.status === "assigned").length;
  const totalValue = assets.reduce((s, a) => s + Number(a.book_value ?? 0), 0);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Assets</h1>
          <p className="text-xs text-mute">Company asset register · assignments · book value</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowDep(!showDep)}
            className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-mute hover:text-ink"
          >
            {showDep ? "Hide" : "Finance & depreciation"}
          </button>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2"
          >
            + New asset
          </button>
        </div>
      </div>

      {showDep && dep && (
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <div className="flex flex-wrap items-center gap-4 border-b border-line px-4 py-3">
            <span className="text-sm font-semibold text-ink">Finance &amp; depreciation</span>
            <span className="text-[11px] text-mute">
              Cost <span className="font-semibold text-ink">{inr(dep.total_cost)}</span> ·
              Book value <span className="font-semibold text-green">{inr(dep.total_book_value)}</span> ·
              Depreciated <span className="font-semibold text-warn-strong">{inr(dep.total_depreciated)}</span>
            </span>
          </div>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
                <th className="px-4 py-2 font-semibold">Asset</th>
                <th className="px-3 py-2 font-semibold">Cost</th>
                <th className="px-3 py-2 font-semibold">Book value</th>
                <th className="px-3 py-2 font-semibold">Depreciated</th>
              </tr>
            </thead>
            <tbody>
              {dep.lines.map((l) => (
                <tr key={l.id} className="border-b border-line-2 last:border-0">
                  <td className="px-4 py-2">
                    <span className="font-mono text-[10px] text-mute">{l.asset_tag}</span>
                    <span className="ml-2 text-ink">{l.name}</span>
                  </td>
                  <td className="px-3 py-2 text-mute">{inr(l.purchase_cost)}</td>
                  <td className="px-3 py-2 font-semibold text-ink">{inr(l.book_value)}</td>
                  <td className="px-3 py-2 text-warn-strong">{inr(l.depreciated)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">Total assets</div>
          <div className="text-2xl font-semibold text-ink">{assets.length}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">In stock</div>
          <div className="text-2xl font-semibold text-green">{inStock}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">Assigned</div>
          <div className="text-2xl font-semibold text-blue-strong">{assigned}</div>
        </div>
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">Book value</div>
          <div className="text-2xl font-semibold text-ink">{inr(totalValue)}</div>
        </div>
      </div>

      {showAdd && (
        <form onSubmit={add} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <input name="asset_tag" required placeholder="Asset tag" className="rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="name" required placeholder="Name / model" className="min-w-40 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <select name="category" className="rounded-lg border border-line px-2 py-2 text-sm capitalize">
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <input name="serial_no" placeholder="Serial no" className="rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="purchase_date" type="date" className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
          <input name="purchase_cost" type="number" min="0" step="1" placeholder="Cost ₹" className="w-28 rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Register</button>
        </form>
      )}

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">Asset</th>
              <th className="px-3 py-2 font-semibold">Category</th>
              <th className="px-3 py-2 font-semibold">Holder</th>
              <th className="px-3 py-2 font-semibold">Book value</th>
              <th className="px-3 py-2 font-semibold">Status</th>
              <th className="px-3 py-2 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id} className="border-b border-line-2 last:border-0">
                <td className="px-4 py-2">
                  <span className="block font-medium text-ink">{a.name}</span>
                  <span className="block font-mono text-[10px] text-mute">
                    {a.asset_tag}{a.serial_no ? ` · ${a.serial_no}` : ""}
                  </span>
                </td>
                <td className="px-3 py-2 capitalize text-mute">{a.category}</td>
                <td className="px-3 py-2 text-ink">{a.holder_name ?? "—"}</td>
                <td className="px-3 py-2 font-mono text-xs text-ink">{inr(a.book_value)}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLE[a.status]}`}>
                    {a.status.replace("_", " ")}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  {a.status === "in_stock" && (
                    assigning === a.id ? (
                      <select
                        autoFocus
                        defaultValue=""
                        onChange={(e) => e.target.value && assign(a.id, Number(e.target.value))}
                        onBlur={() => setAssigning(null)}
                        className="rounded-md border border-line px-2 py-1 text-[11px]"
                      >
                        <option value="" disabled>Assign to…</option>
                        {employees.map((emp) => (
                          <option key={emp.employee_id} value={emp.employee_id}>
                            {emp.full_name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <button
                        onClick={() => setAssigning(a.id)}
                        className="rounded-md bg-blue-soft px-2 py-1 text-[11px] font-medium text-blue-strong"
                      >
                        Assign
                      </button>
                    )
                  )}
                  {a.status === "assigned" && (
                    <button
                      onClick={() => doReturn(a.id)}
                      className="rounded-md border border-line px-2 py-1 text-[11px] font-medium text-mute hover:text-ink"
                    >
                      Return
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {assets.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-mute">
                  No assets registered yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
