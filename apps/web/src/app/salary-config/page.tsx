"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createSalaryComponent,
  deactivateSalaryComponent,
  fetchSalaryComponents,
  previewSalaryStructure,
  type CalcType,
  type ComponentType,
  type SalaryComponent,
  type SalaryConfigPreview,
} from "@/lib/api";

const TABS: { key: ComponentType; label: string; blurb: string }[] = [
  { key: "earning", label: "Earnings", blurb: "Paid in gross — basic, allowances" },
  { key: "reimbursement", label: "Reimbursements", blurb: "Tax-friendly bill-based payouts" },
  { key: "deduction", label: "Deductions", blurb: "Recovered from gross" },
  { key: "employer", label: "Employer cost", blurb: "CTC, not paid in gross — PF, gratuity" },
];

const CALC_LABEL: Record<CalcType, string> = {
  fixed: "Fixed ₹",
  pct_ctc: "% of CTC",
  pct_basic: "% of Basic",
  pct_gross: "% of Gross",
  balancing: "Balancing",
};

const TAX_STYLE: Record<SalaryComponent["tax_treatment"], string> = {
  taxable: "bg-red-soft text-red-strong",
  partial: "bg-warn-soft text-warn-strong",
  exempt: "bg-green-soft text-green-strong",
};

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export default function SalaryConfigPage() {
  const [components, setComponents] = useState<SalaryComponent[]>([]);
  const [tab, setTab] = useState<ComponentType>("earning");
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [preview, setPreview] = useState<SalaryConfigPreview | null>(null);
  const [ctc, setCtc] = useState("1200000");

  const reload = useCallback(() => {
    fetchSalaryComponents().then(setComponents).catch((e) => setError(e.message));
  }, []);

  const runPreview = useCallback((value: string) => {
    if (!value || Number(value) <= 0) {
      setPreview(null);
      return;
    }
    previewSalaryStructure(value).then(setPreview).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    reload();
    previewSalaryStructure("1200000").then(setPreview).catch((e) => setError(e.message));
  }, [reload]);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await createSalaryComponent({
        code: (fd.get("code") as string).toUpperCase(),
        name: fd.get("name") as string,
        component_type: tab,
        calc_type: fd.get("calc_type") as CalcType,
        value: (fd.get("value") as string) || "0",
        tax_treatment: fd.get("tax_treatment") as "taxable" | "partial" | "exempt",
        pf_wage: fd.get("pf_wage") === "on",
        esi_wage: fd.get("esi_wage") === "on",
        pt_wage: fd.get("pt_wage") === "on",
      });
      form.reset();
      setShowAdd(false);
      reload();
      runPreview(ctc);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function remove(c: SalaryComponent) {
    if (!confirm(`Deactivate component "${c.code}"?`)) return;
    try {
      await deactivateSalaryComponent(c.id);
      reload();
      runPreview(ctc);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const rows = components.filter((c) => c.component_type === tab);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Salary configuration</h1>
          <p className="text-xs text-mute">
            Component catalogue · calc rules · statutory wages · CTC structure preview
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2"
        >
          + New component
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        {/* ---- component catalogue with tabs ---- */}
        <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <div className="flex border-b border-line">
            {TABS.map((t) => {
              const count = components.filter((c) => c.component_type === t.key).length;
              const active = tab === t.key;
              return (
                <button
                  key={t.key}
                  onClick={() => {
                    setTab(t.key);
                    setShowAdd(false);
                  }}
                  className={`flex-1 px-3 py-2.5 text-center text-xs font-medium transition ${
                    active
                      ? "border-b-2 border-ink text-ink"
                      : "text-mute hover:text-ink"
                  }`}
                >
                  {t.label}
                  <span className="ml-1 text-[10px] text-mute-2">{count}</span>
                </button>
              );
            })}
          </div>

          <div className="px-4 py-2 text-[11px] text-mute">
            {TABS.find((t) => t.key === tab)?.blurb}
          </div>

          {showAdd && (
            <form
              onSubmit={add}
              className="flex flex-wrap items-end gap-3 border-y border-line bg-canvas p-4"
            >
              <input
                name="code"
                required
                placeholder="CODE"
                className="w-28 rounded-lg border border-line px-3 py-2 font-mono text-sm uppercase"
              />
              <input
                name="name"
                required
                placeholder="Display name"
                className="min-w-40 flex-1 rounded-lg border border-line px-3 py-2 text-sm"
              />
              <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                Calc
                <select
                  name="calc_type"
                  defaultValue="fixed"
                  className="mt-1 block rounded-lg border border-line px-2 py-1.5 text-sm"
                >
                  {(Object.keys(CALC_LABEL) as CalcType[]).map((k) => (
                    <option key={k} value={k}>{CALC_LABEL[k]}</option>
                  ))}
                </select>
              </label>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                Value
                <input
                  name="value"
                  type="number"
                  min="0"
                  step="0.01"
                  defaultValue="0"
                  className="mt-1 block w-24 rounded-lg border border-line px-2 py-1.5 text-sm"
                />
              </label>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                Tax
                <select
                  name="tax_treatment"
                  defaultValue="taxable"
                  className="mt-1 block rounded-lg border border-line px-2 py-1.5 text-sm"
                >
                  <option value="taxable">Taxable</option>
                  <option value="partial">Partial</option>
                  <option value="exempt">Exempt</option>
                </select>
              </label>
              <div className="flex items-center gap-3 text-[11px] text-mute">
                <label className="flex items-center gap-1">
                  <input name="pf_wage" type="checkbox" /> PF
                </label>
                <label className="flex items-center gap-1">
                  <input name="esi_wage" type="checkbox" /> ESI
                </label>
                <label className="flex items-center gap-1">
                  <input name="pt_wage" type="checkbox" /> PT
                </label>
              </div>
              <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">
                Add
              </button>
            </form>
          )}

          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
                <th className="px-4 py-2 font-semibold">Component</th>
                <th className="px-3 py-2 font-semibold">Calc</th>
                <th className="px-3 py-2 font-semibold">Wages</th>
                <th className="px-3 py-2 font-semibold">Tax</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-b border-line-2 last:border-0">
                  <td className="px-4 py-2">
                    <span className="font-mono text-[11px] text-mute">{c.code}</span>
                    <span className="ml-2 font-medium text-ink">{c.name}</span>
                  </td>
                  <td className="px-3 py-2 text-mute">
                    {CALC_LABEL[c.calc_type]}
                    {c.calc_type !== "balancing" && (
                      <span className="ml-1 font-semibold text-ink">
                        {c.calc_type === "fixed" ? inr(c.value) : `${Number(c.value)}%`}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span className="flex gap-1">
                      {c.pf_wage && (
                        <span className="rounded bg-indigo-soft px-1 text-[9px] font-semibold text-indigo-strong">PF</span>
                      )}
                      {c.esi_wage && (
                        <span className="rounded bg-blue-soft px-1 text-[9px] font-semibold text-blue-strong">ESI</span>
                      )}
                      {c.pt_wage && (
                        <span className="rounded bg-pink-soft px-1 text-[9px] font-semibold text-pink-strong">PT</span>
                      )}
                      {!c.pf_wage && !c.esi_wage && !c.pt_wage && (
                        <span className="text-[11px] text-mute-2">—</span>
                      )}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${TAX_STYLE[c.tax_treatment]}`}>
                      {c.tax_treatment}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => remove(c)}
                      className="text-[11px] text-mute hover:text-red-strong"
                    >
                      Deactivate
                    </button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-mute">
                    No {tab} components yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        {/* ---- live CTC preview ---- */}
        <section className="h-fit overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
            Structure preview
          </div>
          <div className="space-y-3 p-4">
            <label className="block text-[10px] font-semibold uppercase tracking-wider text-mute">
              Annual CTC (₹)
              <input
                type="number"
                min="0"
                step="10000"
                value={ctc}
                onChange={(e) => {
                  setCtc(e.target.value);
                  runPreview(e.target.value);
                }}
                className="mt-1 block w-full rounded-lg border border-line px-3 py-2 text-sm"
              />
            </label>

            {preview ? (
              <>
                <div className="rounded-lg bg-canvas px-3 py-2 text-[11px] text-mute">
                  Monthly CTC <span className="font-semibold text-ink">{inr(preview.monthly_ctc)}</span>
                </div>
                <table className="w-full text-left text-sm">
                  <tbody>
                    {preview.lines.map((l) => (
                      <tr key={l.code} className="border-b border-line-2 last:border-0">
                        <td className="py-1.5">
                          <span className="font-mono text-[10px] text-mute">{l.code}</span>
                          <span className="ml-2 text-ink">{l.name}</span>
                        </td>
                        <td className="py-1.5 text-right font-mono text-ink">{inr(l.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 border-line">
                      <td className="py-2 text-xs font-semibold uppercase tracking-wider text-mute">
                        Gross / month
                      </td>
                      <td className="py-2 text-right text-base font-semibold text-green">
                        {inr(preview.gross_monthly)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
                <p className="text-[10px] text-mute-2">
                  Balancing component absorbs CTC minus employer cost (PF) and the other
                  earnings. Reimbursements resolve at their fixed cap.
                </p>
              </>
            ) : (
              <p className="py-6 text-center text-sm text-mute">Enter a CTC to preview.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
