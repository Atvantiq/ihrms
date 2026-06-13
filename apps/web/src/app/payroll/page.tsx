"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createRun,
  downloadFile,
  fetchEmployees,
  fetchRegister,
  fetchRuns,
  finalizeRun,
  markRunPaid,
  previewStructure,
  setStructure,
  type EmployeeListItem,
  type PayrollRun,
  type Payslip,
  type StructurePreview,
} from "@/lib/api";

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

function SalaryPanel({ employees }: { employees: EmployeeListItem[] }) {
  const [emp, setEmp] = useState("");
  const [ctc, setCtc] = useState("");
  const [regime, setRegime] = useState<"new" | "old">("new");
  const [preview, setPreview] = useState<StructurePreview | null>(null);
  const [tds, setTds] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    const n = Number(ctc);
    const t = setTimeout(() => {
      if (n > 0) {
        previewStructure(n).then(setPreview).catch(() => setPreview(null));
      } else {
        setPreview(null);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [ctc]);

  async function save() {
    if (!emp || !ctc) return;
    try {
      const saved = await setStructure(Number(emp), Number(ctc), "2026-04-01", regime);
      setTds(saved.monthly_tds);
      setMsg("Saved ✓");
      setTimeout(() => setMsg(null), 2500);
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  return (
    <section className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-ink">Set salary (CTC)</h2>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-48 flex-1">
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
            Employee
          </label>
          <select
            value={emp}
            onChange={(e) => setEmp(e.target.value)}
            className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm"
          >
            <option value="">Select…</option>
            {employees.map((m) => (
              <option key={m.employee_id} value={m.employee_id}>
                {m.full_name} ({m.employee_code})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
            Annual CTC (₹)
          </label>
          <input
            value={ctc}
            onChange={(e) => setCtc(e.target.value.replace(/\D/g, ""))}
            placeholder="1800000"
            className="w-36 rounded-lg border border-line bg-surface px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
            Tax regime
          </label>
          <select
            value={regime}
            onChange={(e) => setRegime(e.target.value as "new" | "old")}
            className="rounded-lg border border-line bg-surface px-2 py-2 text-sm"
          >
            <option value="new">New</option>
            <option value="old">Old</option>
          </select>
        </div>
        <button
          onClick={save}
          disabled={!emp || !ctc}
          className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface hover:bg-ink-2 disabled:opacity-50"
        >
          Save
        </button>
        {msg && <span className="text-xs text-green-strong">{msg}</span>}
      </div>
      {preview && (
        <div className="mt-3 flex flex-wrap gap-4 rounded-lg bg-line-2 px-3 py-2 text-xs text-mute">
          <span>Basic <b className="text-ink">{inr(preview.basic)}</b></span>
          <span>HRA <b className="text-ink">{inr(preview.hra)}</b></span>
          <span>Special <b className="text-ink">{inr(preview.special_allowance)}</b></span>
          <span>Gross/mo <b className="text-ink">{inr(preview.gross_monthly)}</b></span>
          {tds !== null && (
            <span>
              Monthly TDS <b className="text-red-strong">{inr(tds)}</b>{" "}
              <span className="text-mute-2">({regime} regime)</span>
            </span>
          )}
        </div>
      )}
    </section>
  );
}

function Register({ runId }: { runId: string }) {
  const [rows, setRows] = useState<Payslip[]>([]);
  useEffect(() => {
    fetchRegister(runId).then(setRows).catch(() => setRows([]));
  }, [runId]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
            <th className="px-4 py-2 font-semibold">Employee</th>
            <th className="px-3 py-2 font-semibold">Basic</th>
            <th className="px-3 py-2 font-semibold">HRA</th>
            <th className="px-3 py-2 font-semibold">Special</th>
            <th className="px-3 py-2 font-semibold">Gross</th>
            <th className="px-3 py-2 font-semibold">PF</th>
            <th className="px-3 py-2 font-semibold">PT</th>
            <th className="px-3 py-2 font-semibold">TDS</th>
            <th className="px-3 py-2 font-semibold">Net pay</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.employee_id} className="border-b border-line-2 last:border-0">
              <td className="px-4 py-2 font-medium text-ink">{p.employee_name}</td>
              <td className="px-3 py-2 text-mute">{inr(p.earnings.basic ?? 0)}</td>
              <td className="px-3 py-2 text-mute">{inr(p.earnings.hra ?? 0)}</td>
              <td className="px-3 py-2 text-mute">{inr(p.earnings.special_allowance ?? 0)}</td>
              <td className="px-3 py-2 text-ink">{inr(p.gross)}</td>
              <td className="px-3 py-2 text-red-strong">{inr(p.deductions.pf_employee ?? 0)}</td>
              <td className="px-3 py-2 text-red-strong">{inr(p.deductions.pt ?? 0)}</td>
              <td className="px-3 py-2 text-red-strong">{inr(p.deductions.tds ?? 0)}</td>
              <td className="px-3 py-2 font-semibold text-ink">{inr(p.net_pay)}</td>
              <td className="px-3 py-2 text-right">
                <button
                  onClick={() =>
                    downloadFile(
                      `/payroll/payslips/${p.employee_id}/pdf/${runId}`,
                      `payslip_${p.employee_id}.pdf`,
                    )
                  }
                  className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-ink"
                >
                  PDF
                </button>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={10} className="px-4 py-6 text-center text-mute">
                No payslips — set salary structures, then run payroll.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function PayrollPage() {
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [openRun, setOpenRun] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const reload = useCallback(() => {
    fetchRuns().then(setRuns).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    reload();
    fetchEmployees({}).then((d) => setEmployees(d.items)).catch(() => {});
  }, [reload]);

  async function run() {
    try {
      await createRun(year, month, 30);
      setError(null);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function finalize(id: string) {
    try {
      await finalizeRun(id);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function markPaid(id: string) {
    try {
      await markRunPaid(id);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-ink">Payroll</h1>
        <p className="text-xs text-mute">
          Salary structures · monthly runs · India statutory (PF / ESI / PT)
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}{" "}
          <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <SalaryPanel employees={employees} />

      <section className="rounded-xl border border-line bg-surface p-4 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-sm font-semibold text-ink">Run payroll</h2>
          <div className="flex items-end gap-2">
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"
            >
              {MONTHS.map((m, i) => (
                <option key={m} value={i + 1}>{m}</option>
              ))}
            </select>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="w-20 rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"
            />
            <button
              onClick={run}
              className="rounded-lg bg-ink px-4 py-1.5 text-sm font-medium text-surface hover:bg-ink-2"
            >
              Run
            </button>
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
          Payroll runs <span className="font-normal text-mute">({runs.length})</span>
        </div>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">Period</th>
              <th className="px-3 py-2 font-semibold">Employees</th>
              <th className="px-3 py-2 font-semibold">Total gross</th>
              <th className="px-3 py-2 font-semibold">Total net</th>
              <th className="px-3 py-2 font-semibold">Status</th>
              <th className="px-3 py-2 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <>
                <tr key={r.id} className="border-b border-line-2">
                  <td className="px-4 py-2 font-medium text-ink">
                    {MONTHS[r.period_month - 1]} {r.period_year}
                  </td>
                  <td className="px-3 py-2 text-mute">{r.employee_count}</td>
                  <td className="px-3 py-2 text-mute">{inr(r.total_gross)}</td>
                  <td className="px-3 py-2 font-semibold text-ink">{inr(r.total_net)}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${
                        r.status === "finalized"
                          ? "bg-green-soft text-green-strong"
                          : "bg-warn-soft text-warn-strong"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex justify-end gap-1.5">
                      <button
                        onClick={() => setOpenRun(openRun === r.id ? null : r.id)}
                        className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-ink"
                      >
                        {openRun === r.id ? "Hide" : "Register"}
                      </button>
                      <button
                        onClick={() =>
                          downloadFile(
                            `/payroll/runs/${r.id}/bankfile`,
                            `bankfile_${MONTHS[r.period_month - 1]}${r.period_year}.csv`,
                          )
                        }
                        className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-ink"
                      >
                        Bank file
                      </button>
                      {r.status === "draft" && (
                        <button
                          onClick={() => finalize(r.id)}
                          className="rounded-md bg-green-soft px-2 py-1 text-[11px] font-medium text-green-strong hover:opacity-80"
                        >
                          Finalize
                        </button>
                      )}
                      {r.status === "finalized" && (
                        <button
                          onClick={() => markPaid(r.id)}
                          className="rounded-md bg-ink px-2 py-1 text-[11px] font-medium text-surface hover:bg-ink-2"
                        >
                          Mark paid
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
                {openRun === r.id && (
                  <tr key={r.id + "-reg"}>
                    <td colSpan={6} className="bg-canvas px-4 py-2">
                      <Register runId={r.id} />
                    </td>
                  </tr>
                )}
              </>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-mute">
                  No payroll runs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
