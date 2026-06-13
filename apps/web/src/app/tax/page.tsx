"use client";

import { useCallback, useEffect, useState } from "react";
import {
  decideTaxDeclaration,
  fetchMe,
  fetchPendingTaxDeclarations,
  fetchTaxDeclaration,
  fetchTaxSections,
  saveTaxDeclaration,
  submitTaxDeclaration,
  type PendingTaxDecl,
  type TaxDeclaration,
  type TaxSection,
} from "@/lib/api";

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

const STATUS_STYLE: Record<TaxDeclaration["status"], string> = {
  draft: "bg-line-2 text-mute",
  submitted: "bg-warn-soft text-warn-strong",
  approved: "bg-green-soft text-green-strong",
  rejected: "bg-red-soft text-red-strong",
};

export default function TaxPage() {
  const [sections, setSections] = useState<TaxSection[]>([]);
  const [decl, setDecl] = useState<TaxDeclaration | null>(null);
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [regime, setRegime] = useState<"old" | "new">("old");
  const [isHr, setIsHr] = useState(false);
  const [pending, setPending] = useState<PendingTaxDecl[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const loadDecl = useCallback(() => {
    fetchTaxDeclaration()
      .then((d) => {
        setDecl(d);
        setRegime(d.regime);
        setAmounts(Object.fromEntries(d.items.map((i) => [i.section, i.amount])));
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    fetchTaxSections().then(setSections).catch(() => {});
    loadDecl();
    fetchMe().then((me) => {
      setIsHr(me.is_hr);
      if (me.is_hr) fetchPendingTaxDeclarations().then(setPending).catch(() => {});
    });
  }, [loadDecl]);

  const editable = decl?.status === "draft" || decl?.status === "rejected" || !decl?.id;

  async function save(submit: boolean) {
    try {
      const items = sections
        .map((s) => ({ section: s.key, amount: amounts[s.key] || "0" }))
        .filter((i) => Number(i.amount) > 0);
      await saveTaxDeclaration({ regime, items });
      if (submit) await submitTaxDeclaration();
      setMsg(submit ? "Declaration submitted for approval" : "Draft saved");
      setTimeout(() => setMsg(null), 3000);
      loadDecl();
      if (isHr) fetchPendingTaxDeclarations().then(setPending).catch(() => {});
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function decide(id: string, action: "approve" | "reject") {
    try {
      await decideTaxDeclaration(id, action);
      fetchPendingTaxDeclarations().then(setPending).catch(() => {});
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Tax declaration</h1>
          <p className="text-xs text-mute">
            Declare your investments (Chapter VI-A) {decl ? `· FY ${decl.fy}` : ""} — lowers your
            monthly TDS once approved
          </p>
        </div>
        {decl && (
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${STATUS_STYLE[decl.status]}`}>
            {decl.status}
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}
      {msg && (
        <div className="rounded-xl border border-green-soft bg-green-soft/40 p-3 text-sm text-green-strong">
          {msg}
        </div>
      )}

      <section className="rounded-xl border border-line bg-surface shadow-sm">
        <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="text-sm font-semibold text-ink">Investments &amp; deductions</h2>
          <label className="flex items-center gap-2 text-xs text-mute">
            Regime
            <select
              value={regime}
              disabled={!editable}
              onChange={(e) => setRegime(e.target.value as "old" | "new")}
              className="rounded-lg border border-line px-2 py-1 text-sm disabled:opacity-60"
            >
              <option value="old">Old (deductions apply)</option>
              <option value="new">New (no deductions)</option>
            </select>
          </label>
        </div>
        <div className="divide-y divide-line-2">
          {sections.map((s) => (
            <div key={s.key} className="flex items-center justify-between gap-4 px-4 py-3">
              <div className="min-w-0">
                <div className="text-sm font-medium text-ink">{s.label}</div>
                <div className="text-[10px] text-mute-2">
                  {Number(s.cap) > 0 ? `Capped at ${inr(s.cap)}` : "No upper limit"}
                </div>
              </div>
              <input
                type="number"
                min="0"
                step="1"
                disabled={!editable || regime === "new"}
                value={amounts[s.key] ?? ""}
                onChange={(e) => setAmounts({ ...amounts, [s.key]: e.target.value })}
                placeholder="₹0"
                className="w-32 rounded-lg border border-line px-3 py-2 text-right text-sm disabled:bg-line-2/40"
              />
            </div>
          ))}
        </div>
        {decl && (
          <div className="flex items-center justify-between border-t border-line px-4 py-3">
            <div className="text-sm">
              <span className="text-mute">Declared </span>
              <span className="font-semibold text-ink">{inr(decl.declared_total)}</span>
              <span className="ml-3 text-mute">Eligible deduction </span>
              <span className="font-semibold text-green">{inr(decl.eligible_deduction)}</span>
            </div>
            {editable && (
              <div className="flex gap-2">
                <button onClick={() => save(false)} className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-ink hover:bg-line-2">
                  Save draft
                </button>
                <button onClick={() => save(true)} className="rounded-lg bg-ink px-4 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
                  Submit
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      {isHr && pending.length > 0 && (
        <section className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
            Pending approvals <span className="font-normal text-mute">({pending.length})</span>
          </div>
          <div className="divide-y divide-line-2">
            {pending.map((p) => (
              <div key={p.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <span className="text-ink">
                  {p.employee_name ?? p.employee_id}
                  <span className="ml-2 text-[11px] text-mute">
                    FY {p.fy} · {p.regime} · eligible {inr(p.eligible_deduction)}
                  </span>
                </span>
                <div className="flex gap-1.5">
                  <button onClick={() => decide(p.id, "reject")} className="rounded-md border border-line px-2 py-1 text-[11px] font-medium text-mute hover:text-red-strong">
                    Reject
                  </button>
                  <button onClick={() => decide(p.id, "approve")} className="rounded-md bg-ink px-3 py-1 text-[11px] font-medium text-surface">
                    Approve
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
