"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addMaintenance,
  approveAssetRequest,
  assignAsset,
  createAsset,
  fetchAssetRequests,
  fetchAssets,
  fetchDepreciation,
  fetchEmployees,
  fetchMaintenance,
  rejectAssetRequest,
  returnAsset,
  type Asset,
  type AssetRequest,
  type DepreciationReport,
  type EmployeeListItem,
  type Maintenance,
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

function RequestsPanel({
  stock,
  onError,
  onChanged,
}: {
  stock: Asset[];
  onError: (m: string) => void;
  onChanged: () => void;
}) {
  const [reqs, setReqs] = useState<AssetRequest[]>([]);
  const load = useCallback(() => {
    fetchAssetRequests("all").then(setReqs).catch((e) => onError(e.message));
  }, [onError]);
  useEffect(() => load(), [load]);

  async function approve(r: AssetRequest, assetId: string) {
    try {
      await approveAssetRequest(r.id, assetId || undefined);
      load();
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function reject(r: AssetRequest) {
    try {
      await rejectAssetRequest(r.id);
      load();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  const STATUS: Record<string, string> = {
    pending: "bg-warn-soft text-warn-strong",
    approved: "bg-blue-soft text-blue-strong",
    fulfilled: "bg-green-soft text-green-strong",
    rejected: "bg-red-soft text-red-strong",
  };

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
        Asset requests <span className="font-normal text-mute">({reqs.length})</span>
      </div>
      <table className="w-full text-left text-sm">
        <tbody>
          {reqs.map((r) => {
            const matching = stock.filter((a) => a.category === r.category);
            return (
              <tr key={r.id} className="border-b border-line-2 last:border-0">
                <td className="px-4 py-2">
                  <span className="text-ink">{r.employee_name ?? r.employee_id}</span>
                  <span className="ml-2 text-[11px] capitalize text-mute">{r.category}</span>
                  <span className="ml-2 text-[11px] text-mute-2">{r.justification}</span>
                </td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS[r.status]}`}>
                    {r.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  {r.status === "pending" && (
                    <span className="flex items-center justify-end gap-2">
                      <select
                        defaultValue=""
                        onChange={(e) => e.target.value && approve(r, e.target.value)}
                        className="rounded-md border border-line px-2 py-1 text-[11px]"
                      >
                        <option value="">Approve + allocate…</option>
                        <option value="__none__" disabled>
                          {matching.length} in stock
                        </option>
                        {matching.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.asset_tag} · {a.name}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => approve(r, "")}
                        className="rounded-md bg-blue-soft px-2 py-1 text-[11px] font-medium text-blue-strong"
                      >
                        Approve only
                      </button>
                      <button
                        onClick={() => reject(r)}
                        className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-red-strong"
                      >
                        Reject
                      </button>
                    </span>
                  )}
                  {r.status !== "pending" && r.decision_note && (
                    <span className="text-[11px] text-mute">{r.decision_note}</span>
                  )}
                </td>
              </tr>
            );
          })}
          {reqs.length === 0 && (
            <tr>
              <td className="px-4 py-8 text-center text-sm text-mute">No asset requests.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

function MaintenancePanel({ asset, onError }: { asset: Asset; onError: (m: string) => void }) {
  const [log, setLog] = useState<Maintenance[]>([]);
  const load = useCallback(() => {
    fetchMaintenance(asset.id).then(setLog).catch((e) => onError(e.message));
  }, [asset.id, onError]);
  useEffect(() => load(), [load]);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await addMaintenance(asset.id, {
        kind: fd.get("kind") as string,
        performed_on: fd.get("performed_on") as string,
        cost: (fd.get("cost") as string) || "0",
        vendor: (fd.get("vendor") as string) || null,
        note: (fd.get("note") as string) || null,
      });
      e.currentTarget.reset();
      load();
    } catch (err) {
      onError((err as Error).message);
    }
  }

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
        Maintenance · {asset.name}{" "}
        <span className="font-mono text-[11px] text-mute">{asset.asset_tag}</span>
      </div>
      <form onSubmit={add} className="flex flex-wrap items-end gap-2 border-b border-line bg-canvas p-3">
        <select name="kind" defaultValue="service" className="rounded-lg border border-line px-2 py-1.5 text-sm capitalize">
          {["service", "repair", "upgrade", "inspection"].map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
        <input name="performed_on" type="date" required className="rounded-lg border border-line px-2 py-1.5 text-sm" />
        <input name="cost" type="number" min="0" step="1" placeholder="Cost ₹" className="w-24 rounded-lg border border-line px-2 py-1.5 text-sm" />
        <input name="vendor" placeholder="Vendor" className="rounded-lg border border-line px-2 py-1.5 text-sm" />
        <input name="note" placeholder="Note" className="min-w-32 flex-1 rounded-lg border border-line px-2 py-1.5 text-sm" />
        <button className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface">Log</button>
      </form>
      <div className="divide-y divide-line-2">
        {log.map((m) => (
          <div key={m.id} className="flex items-center justify-between px-4 py-2 text-sm">
            <span className="text-ink capitalize">
              {m.kind}
              {m.vendor && <span className="ml-2 text-[11px] text-mute">{m.vendor}</span>}
              {m.note && <span className="ml-2 text-[11px] text-mute-2">{m.note}</span>}
            </span>
            <span className="text-[11px] text-mute">
              {m.performed_on} · <span className="font-semibold text-ink">{inr(m.cost)}</span>
            </span>
          </div>
        ))}
        {log.length === 0 && (
          <div className="px-4 py-6 text-center text-sm text-mute">No maintenance logged.</div>
        )}
      </div>
    </section>
  );
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [assigning, setAssigning] = useState<string | null>(null);
  const [dep, setDep] = useState<DepreciationReport | null>(null);
  const [showDep, setShowDep] = useState(false);
  const [showReqs, setShowReqs] = useState(false);
  const [maintaining, setMaintaining] = useState<Asset | null>(null);

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
            onClick={() => setShowReqs(!showReqs)}
            className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-mute hover:text-ink"
          >
            {showReqs ? "Hide" : "Requests"}
          </button>
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

      {showReqs && (
        <RequestsPanel
          stock={assets.filter((a) => a.status === "in_stock")}
          onError={setError}
          onChanged={reload}
        />
      )}

      {maintaining && <MaintenancePanel asset={maintaining} onError={setError} />}

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
                  <button
                    onClick={() => setMaintaining(maintaining?.id === a.id ? null : a)}
                    className="ml-1 rounded-md border border-line px-2 py-1 text-[11px] font-medium text-mute hover:text-ink"
                  >
                    🔧
                  </button>
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
