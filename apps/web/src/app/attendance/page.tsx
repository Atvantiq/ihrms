"use client";

import { useCallback, useEffect, useState } from "react";
import {
  availCompOff,
  earnCompOff,
  fetchAttendance,
  fetchCompOff,
  fetchDuty,
  fetchEmployees,
  fetchMe,
  fetchOvertime,
  fetchRegularizations,
  logOvertime,
  markAttendance,
  requestDuty,
  requestRegularization,
  type AttendanceSummary,
  type CompOff,
  type Duty,
  type EmployeeListItem,
  type Overtime,
  type Regularization,
} from "@/lib/api";

const DUTY_STATUS_STYLE: Record<Duty["status"], string> = {
  pending: "bg-warn-soft text-warn-strong",
  approved: "bg-green-soft text-green-strong",
  rejected: "bg-red-soft text-red-strong",
};

const CO_STATUS_STYLE: Record<CompOff["status"], string> = {
  pending: "bg-warn-soft text-warn-strong",
  approved: "bg-green-soft text-green-strong",
  rejected: "bg-red-soft text-red-strong",
  availed: "bg-blue-soft text-blue-strong",
  expired: "bg-line-2 text-mute",
};

const REG_STATUS_STYLE: Record<Regularization["status"], string> = {
  pending: "bg-warn-soft text-warn-strong",
  approved: "bg-green-soft text-green-strong",
  rejected: "bg-red-soft text-red-strong",
};

const OT_STATUS_STYLE: Record<Overtime["status"], string> = {
  pending: "bg-warn-soft text-warn-strong",
  approved: "bg-green-soft text-green-strong",
  rejected: "bg-red-soft text-red-strong",
  paid: "bg-blue-soft text-blue-strong",
};

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const STATUS_STYLE: Record<string, string> = {
  present: "bg-green-soft text-green-strong",
  wfh: "bg-blue-soft text-blue-strong",
  absent: "bg-red-soft text-red-strong",
  leave: "bg-warn-soft text-warn-strong",
  holiday: "bg-indigo-soft text-indigo-strong",
  weekend: "bg-line-2 text-mute-2",
  not_marked: "bg-surface text-mute border border-dashed border-line",
  upcoming: "bg-surface text-mute-2",
};
const STATUS_LABEL: Record<string, string> = {
  present: "P", wfh: "WFH", absent: "A", leave: "L",
  holiday: "H", weekend: "—", not_marked: "·", upcoming: "",
};

function Stat({ label, value, cls }: { label: string; value: number; cls: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-center shadow-sm">
      <div className={`text-lg font-semibold ${cls}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-mute">{label}</div>
    </div>
  );
}

export default function AttendancePage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [me, setMe] = useState<{ employee_id: number; is_hr: boolean } | null>(null);
  const [employees, setEmployees] = useState<EmployeeListItem[]>([]);
  const [empId, setEmpId] = useState<number | null>(null);
  const [data, setData] = useState<AttendanceSummary | null>(null);
  const [regs, setRegs] = useState<Regularization[]>([]);
  const [ot, setOt] = useState<Overtime[]>([]);
  const [compOff, setCompOff] = useState<CompOff[]>([]);
  const [duty, setDuty] = useState<Duty[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMe().then((m) => {
      setMe({ employee_id: m.employee_id, is_hr: m.is_hr });
      setEmpId(m.employee_id);
      if (m.is_hr) fetchEmployees({}).then((d) => setEmployees(d.items)).catch(() => {});
    });
  }, []);

  const reload = useCallback(() => {
    if (!empId) return;
    fetchAttendance(year, month, empId)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [year, month, empId]);

  useEffect(reload, [reload]);

  const loadRegs = useCallback(() => {
    fetchRegularizations("mine").then(setRegs).catch(() => {});
    fetchOvertime("mine").then(setOt).catch(() => {});
    fetchCompOff("mine").then(setCompOff).catch(() => {});
    fetchDuty("mine").then(setDuty).catch(() => {});
  }, []);

  async function submitDuty(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await requestDuty({
        duty_type: fd.get("duty_type") as "wfh" | "on_duty",
        start_date: fd.get("start_date") as string,
        end_date: fd.get("end_date") as string,
        reason: fd.get("reason") as string,
      });
      form.reset();
      loadRegs();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  useEffect(loadRegs, [loadRegs]);

  async function submitCompOff(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await earnCompOff({
        earned_date: fd.get("earned_date") as string,
        reason: fd.get("reason") as string,
      });
      form.reset();
      loadRegs();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  async function avail(id: string) {
    const d = prompt("Avail comp-off on date (YYYY-MM-DD)?");
    if (!d) return;
    try {
      await availCompOff(id, d);
      loadRegs();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function submitOt(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await logOvertime({
        ot_date: fd.get("ot_date") as string,
        hours: fd.get("hours") as string,
        reason: fd.get("reason") as string,
      });
      form.reset();
      loadRegs();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function submitReg(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await requestRegularization({
        work_date: fd.get("work_date") as string,
        requested_status: fd.get("requested_status") as "present" | "wfh",
        reason: fd.get("reason") as string,
      });
      form.reset();
      loadRegs();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function cycle(day: string, current: string) {
    if (!empId || !me) return;
    if (current === "upcoming" || current === "holiday" || current === "weekend") return;
    if (current === "leave") return; // leave is owned by the leave module
    const next =
      current === "present" ? "absent" : current === "absent" ? "wfh" : "present";
    try {
      const updated = await markAttendance(empId, day, next as "present");
      setData(updated);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // leading blanks so day 1 lands under its weekday
  const firstDow = data ? new Date(`${data.year}-${String(data.month).padStart(2, "0")}-01T00:00:00`).getDay() : 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink">Attendance</h1>
          <p className="text-xs text-mute">
            Derived from marks · leave · holidays · weekends — drives payroll LOP
          </p>
        </div>
        <div className="flex items-end gap-2">
          {me?.is_hr && employees.length > 0 && (
            <select
              value={empId ?? ""}
              onChange={(e) => setEmpId(Number(e.target.value))}
              className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm"
            >
              {employees.map((m) => (
                <option key={m.employee_id} value={m.employee_id}>
                  {m.full_name}
                </option>
              ))}
            </select>
          )}
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
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error}{" "}
          <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-7">
            <Stat label="Present" value={data.present} cls="text-green" />
            <Stat label="WFH" value={data.wfh} cls="text-blue-strong" />
            <Stat label="Leave" value={data.leave} cls="text-warn" />
            <Stat label="Holiday" value={data.holiday} cls="text-indigo" />
            <Stat label="Absent" value={data.absent} cls="text-red" />
            <Stat label="LOP" value={data.lop} cls="text-red" />
            <Stat label="Payable" value={data.payable} cls="text-ink" />
          </div>

          <section className="rounded-xl border border-line bg-surface p-4 shadow-sm">
            <div className="mb-2 grid grid-cols-7 gap-1.5 text-center text-[10px] font-semibold uppercase tracking-wide text-mute">
              {DOW.map((d) => <div key={d}>{d}</div>)}
            </div>
            <div className="grid grid-cols-7 gap-1.5">
              {Array.from({ length: firstDow }).map((_, i) => (
                <div key={`b${i}`} />
              ))}
              {data.days.map((d) => {
                const dayNum = Number(d.day.slice(-2));
                return (
                  <button
                    key={d.day}
                    onClick={() => cycle(d.day, d.status)}
                    title={`${d.day} · ${d.status}`}
                    className={`flex aspect-square flex-col items-center justify-center rounded-lg text-sm ${STATUS_STYLE[d.status] ?? "bg-surface"} ${
                      ["present", "absent", "wfh", "not_marked"].includes(d.status)
                        ? "cursor-pointer hover:ring-2 hover:ring-indigo/30"
                        : "cursor-default"
                    }`}
                  >
                    <span className="font-medium">{dayNum}</span>
                    <span className="text-[9px] font-semibold">
                      {STATUS_LABEL[d.status]}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="mt-3 text-[11px] text-mute-2">
              Click a working day to cycle Present → Absent → WFH. Leave and
              holidays are managed in their own screens.
            </p>
          </section>

          <section className="rounded-xl border border-line bg-surface shadow-sm">
            <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
              Regularization requests
              <span className="ml-2 font-normal text-mute">
                fix a missing or wrong day — needs manager approval
              </span>
            </div>
            <form onSubmit={submitReg} className="flex flex-wrap items-end gap-3 border-b border-line-2 p-4">
              <input name="work_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
              <select name="requested_status" className="rounded-lg border border-line px-2 py-2 text-sm">
                <option value="present">Present</option>
                <option value="wfh">WFH</option>
              </select>
              <input name="reason" required maxLength={300} placeholder="Reason" className="min-w-48 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
              <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Request</button>
            </form>
            <div className="divide-y divide-line-2">
              {regs.length === 0 && (
                <p className="px-4 py-3 text-sm text-mute">No regularization requests.</p>
              )}
              {regs.map((r) => (
                <div key={r.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <span className="text-ink">
                    {r.work_date}
                    <span className="ml-2 text-[11px] capitalize text-mute">{r.requested_status}</span>
                    <span className="ml-2 text-[11px] text-mute-2">{r.reason}</span>
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${REG_STATUS_STYLE[r.status]}`}>
                    {r.status}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-line bg-surface shadow-sm">
            <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
              Overtime
              <span className="ml-2 font-normal text-mute">
                log extra hours — paid (hours × rate) once approved
              </span>
            </div>
            <form onSubmit={submitOt} className="flex flex-wrap items-end gap-3 border-b border-line-2 p-4">
              <input name="ot_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
              <input name="hours" type="number" min="0.5" max="24" step="0.5" required placeholder="Hours" className="w-24 rounded-lg border border-line px-3 py-2 text-sm" />
              <input name="reason" required maxLength={300} placeholder="Reason" className="min-w-48 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
              <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Log OT</button>
            </form>
            <div className="divide-y divide-line-2">
              {ot.length === 0 && (
                <p className="px-4 py-3 text-sm text-mute">No overtime logged.</p>
              )}
              {ot.map((o) => (
                <div key={o.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <span className="text-ink">
                    {o.ot_date}
                    <span className="ml-2 text-[11px] text-mute">
                      {Number(o.hours)}h · {Number(o.rate_multiplier)}× · {o.reason}
                    </span>
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${OT_STATUS_STYLE[o.status]}`}>
                    {o.status}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-line bg-surface shadow-sm">
            <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
              Comp-off
              <span className="ml-2 font-normal text-mute">
                worked a holiday/weekend? earn a day off (valid 90 days)
              </span>
            </div>
            <form onSubmit={submitCompOff} className="flex flex-wrap items-end gap-3 border-b border-line-2 p-4">
              <input name="earned_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
              <input name="reason" required maxLength={300} placeholder="Reason (e.g. weekend release)" className="min-w-48 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
              <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Earn comp-off</button>
            </form>
            <div className="divide-y divide-line-2">
              {compOff.length === 0 && (
                <p className="px-4 py-3 text-sm text-mute">No comp-off credits.</p>
              )}
              {compOff.map((c) => (
                <div key={c.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <span className="text-ink">
                    Worked {c.earned_date}
                    <span className="ml-2 text-[11px] text-mute">{c.reason}</span>
                    {c.expiry_date && c.status === "approved" && (
                      <span className="ml-2 text-[11px] text-mute-2">expires {c.expiry_date}</span>
                    )}
                    {c.availed_on && (
                      <span className="ml-2 text-[11px] text-mute-2">availed {c.availed_on}</span>
                    )}
                  </span>
                  <span className="flex items-center gap-2">
                    {c.status === "approved" && (
                      <button onClick={() => avail(c.id)} className="rounded-md border border-line px-2 py-0.5 text-[10px] text-mute hover:text-ink">
                        Avail
                      </button>
                    )}
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${CO_STATUS_STYLE[c.status]}`}>
                      {c.status}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-line bg-surface shadow-sm">
            <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
              Work from home / on-duty
              <span className="ml-2 font-normal text-mute">
                request a date range — attendance is marked once approved
              </span>
            </div>
            <form onSubmit={submitDuty} className="flex flex-wrap items-end gap-3 border-b border-line-2 p-4">
              <select name="duty_type" className="rounded-lg border border-line px-2 py-2 text-sm">
                <option value="wfh">WFH</option>
                <option value="on_duty">On-duty</option>
              </select>
              <input name="start_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
              <input name="end_date" type="date" required className="rounded-lg border border-line px-2 py-2 text-sm text-mute" />
              <input name="reason" required maxLength={300} placeholder="Reason" className="min-w-44 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
              <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Request</button>
            </form>
            <div className="divide-y divide-line-2">
              {duty.length === 0 && <p className="px-4 py-3 text-sm text-mute">No WFH / on-duty requests.</p>}
              {duty.map((d) => (
                <div key={d.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                  <span className="text-ink">
                    {d.duty_type === "wfh" ? "WFH" : "On-duty"}
                    <span className="ml-2 text-[11px] text-mute">{d.start_date} → {d.end_date} · {d.reason}</span>
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${DUTY_STATUS_STYLE[d.status]}`}>
                    {d.status}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
