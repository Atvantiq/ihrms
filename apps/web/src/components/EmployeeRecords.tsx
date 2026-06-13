"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addEmployeeRecord,
  deleteEmployeeRecord,
  fetchEmployeeRecords,
  type EmployeeRecords as Records,
  type RecordResource,
} from "@/lib/api";

type TabKey = RecordResource;

const TABS: { key: TabKey; label: string }[] = [
  { key: "family", label: "Family & nominees" },
  { key: "education", label: "Education" },
  { key: "experience", label: "Experience" },
  { key: "awards", label: "Awards" },
  { key: "training", label: "Training" },
  { key: "incidents", label: "Discipline & safety" },
];

const TRAINING_STYLE: Record<string, string> = {
  completed: "bg-green-soft text-green-strong",
  in_progress: "bg-blue-soft text-blue-strong",
  planned: "bg-line-2 text-mute",
  cancelled: "bg-red-soft text-red-strong",
};
const SEVERITY_STYLE: Record<string, string> = {
  low: "bg-line-2 text-mute",
  medium: "bg-warn-soft text-warn-strong",
  high: "bg-red-soft text-red-strong",
};

function Empty({ label }: { label: string }) {
  return <div className="px-4 py-8 text-center text-sm text-mute">No {label} on record.</div>;
}

function DelBtn({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className="text-[11px] text-mute hover:text-red-strong">
      Remove
    </button>
  );
}

const inputCls = "rounded-lg border border-line px-2 py-1.5 text-sm";

export function EmployeeRecords({
  employeeId,
  isHr,
}: {
  employeeId: number;
  isHr: boolean;
}) {
  const [data, setData] = useState<Records | null>(null);
  const [tab, setTab] = useState<TabKey>("family");
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const reload = useCallback(() => {
    fetchEmployeeRecords(employeeId).then(setData).catch((e) => setError(e.message));
  }, [employeeId]);

  useEffect(() => reload(), [reload]);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const body: Record<string, unknown> = {};
    fd.forEach((v, k) => {
      if (v === "") return;
      if (k === "is_dependent" || k === "is_nominee") body[k] = true;
      else body[k] = v;
    });
    try {
      await addEmployeeRecord(employeeId, tab, body);
      form.reset();
      setAdding(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function remove(resource: RecordResource, id: string) {
    try {
      await deleteEmployeeRecord(employeeId, resource, id);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (!data) return null;

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-5 py-3">
        <h2 className="text-sm font-semibold text-ink">Employee 360 records</h2>
        {data.special_dates.length > 0 && (
          <div className="flex gap-3 text-[11px] text-mute">
            {data.special_dates.map((s) => (
              <span key={s.label}>
                {s.label === "Birthday" ? "🎂" : "🎉"} {s.label}
                <span className="ml-1 font-medium text-ink">
                  {s.in_days === 0 ? "today" : `in ${s.in_days}d`}
                </span>
                {s.years != null && <span className="text-mute-2"> · {s.years}y</span>}
              </span>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="border-b border-line bg-red-soft/30 px-5 py-2 text-xs text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <div className="flex flex-wrap border-b border-line">
        {TABS.map((t) => {
          const count = data[t.key].length;
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => {
                setTab(t.key);
                setAdding(false);
              }}
              className={`px-4 py-2.5 text-xs font-medium transition ${
                active ? "border-b-2 border-ink text-ink" : "text-mute hover:text-ink"
              }`}
            >
              {t.label}
              <span className="ml-1 text-[10px] text-mute-2">{count}</span>
            </button>
          );
        })}
      </div>

      {isHr && (
        <div className="border-b border-line px-5 py-2">
          {adding ? (
            <RecordForm tab={tab} onSubmit={submit} onCancel={() => setAdding(false)} />
          ) : (
            <button
              onClick={() => setAdding(true)}
              className="text-xs font-medium text-blue-strong hover:underline"
            >
              + Add {TABS.find((t) => t.key === tab)?.label.toLowerCase()}
            </button>
          )}
        </div>
      )}

      <div className="px-1 py-1">
        {tab === "family" && (
          data.family.length === 0 ? <Empty label="family members" /> : (
            <table className="w-full text-left text-sm">
              <tbody>
                {data.family.map((f) => (
                  <tr key={f.id} className="border-b border-line-2 last:border-0">
                    <td className="px-4 py-2">
                      <span className="font-medium text-ink">{f.full_name}</span>
                      <span className="ml-2 text-[11px] capitalize text-mute">{f.relation}</span>
                    </td>
                    <td className="px-3 py-2 text-[11px] text-mute">
                      {f.is_dependent && (
                        <span className="mr-1 rounded bg-blue-soft px-1 font-semibold text-blue-strong">
                          dependent
                        </span>
                      )}
                      {f.is_nominee && (
                        <span className="rounded bg-indigo-soft px-1 font-semibold text-indigo-strong">
                          nominee {Number(f.nominee_share)}%
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-mute">{f.date_of_birth ?? ""}</td>
                    <td className="px-3 py-2 text-right">
                      {isHr && <DelBtn onClick={() => remove("family", f.id)} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}

        {tab === "education" && (
          data.education.length === 0 ? <Empty label="education" /> : (
            <table className="w-full text-left text-sm">
              <tbody>
                {data.education.map((ed) => (
                  <tr key={ed.id} className="border-b border-line-2 last:border-0">
                    <td className="px-4 py-2">
                      <span className="font-medium text-ink">{ed.degree}</span>
                      {ed.specialization && (
                        <span className="ml-2 text-[11px] text-mute">{ed.specialization}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-mute">{ed.institution ?? "—"}</td>
                    <td className="px-3 py-2 text-[11px] text-mute">
                      {ed.year_completed ?? ""} {ed.grade ? `· ${ed.grade}` : ""}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isHr && <DelBtn onClick={() => remove("education", ed.id)} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}

        {tab === "experience" && (
          data.experience.length === 0 ? <Empty label="prior experience" /> : (
            <table className="w-full text-left text-sm">
              <tbody>
                {data.experience.map((x) => (
                  <tr key={x.id} className="border-b border-line-2 last:border-0">
                    <td className="px-4 py-2">
                      <span className="font-medium text-ink">{x.employer}</span>
                      {x.designation && (
                        <span className="ml-2 text-[11px] text-mute">{x.designation}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-mute">
                      {x.from_date ?? "?"} → {x.to_date ?? "present"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isHr && <DelBtn onClick={() => remove("experience", x.id)} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}

        {tab === "awards" && (
          data.awards.length === 0 ? <Empty label="awards" /> : (
            <table className="w-full text-left text-sm">
              <tbody>
                {data.awards.map((a) => (
                  <tr key={a.id} className="border-b border-line-2 last:border-0">
                    <td className="px-4 py-2">
                      <span className="font-medium text-ink">{a.title}</span>
                      {a.category && (
                        <span className="ml-2 text-[11px] text-mute">{a.category}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-mute">{a.awarded_on ?? ""}</td>
                    <td className="px-3 py-2 text-right">
                      {isHr && <DelBtn onClick={() => remove("awards", a.id)} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}

        {tab === "training" && (
          data.training.length === 0 ? <Empty label="training" /> : (
            <table className="w-full text-left text-sm">
              <tbody>
                {data.training.map((t) => (
                  <tr key={t.id} className="border-b border-line-2 last:border-0">
                    <td className="px-4 py-2">
                      <span className="font-medium text-ink">{t.program}</span>
                      {t.provider && (
                        <span className="ml-2 text-[11px] text-mute">{t.provider}</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${TRAINING_STYLE[t.status]}`}
                      >
                        {t.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-[11px] text-mute">{t.completed_on ?? ""}</td>
                    <td className="px-3 py-2 text-right">
                      {isHr && <DelBtn onClick={() => remove("training", t.id)} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}

        {tab === "incidents" && (
          data.incidents.length === 0 ? <Empty label="incidents" /> : (
            <table className="w-full text-left text-sm">
              <tbody>
                {data.incidents.map((i) => (
                  <tr key={i.id} className="border-b border-line-2 last:border-0">
                    <td className="px-4 py-2">
                      <span className="font-medium capitalize text-ink">{i.kind}</span>
                      <span className="ml-2 text-[11px] text-mute">{i.description}</span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${SEVERITY_STYLE[i.severity]}`}
                      >
                        {i.severity}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-[11px] text-mute">
                      {i.incident_date} ·{" "}
                      <span className={i.status === "open" ? "text-warn-strong" : "text-mute-2"}>
                        {i.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isHr && <DelBtn onClick={() => remove("incidents", i.id)} />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </div>
    </section>
  );
}

function RecordForm({
  tab,
  onSubmit,
  onCancel,
}: {
  tab: TabKey;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
}) {
  return (
    <form onSubmit={onSubmit} className="flex flex-wrap items-center gap-2 py-1">
      {tab === "family" && (
        <>
          <input name="full_name" required placeholder="Full name" className={inputCls} />
          <select name="relation" className={inputCls} defaultValue="spouse">
            {["spouse", "child", "father", "mother", "sibling", "guardian", "other"].map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <input name="date_of_birth" type="date" className={inputCls} />
          <label className="flex items-center gap-1 text-[11px] text-mute">
            <input name="is_dependent" type="checkbox" /> dependent
          </label>
          <label className="flex items-center gap-1 text-[11px] text-mute">
            <input name="is_nominee" type="checkbox" /> nominee
          </label>
          <input
            name="nominee_share"
            type="number"
            min="0"
            max="100"
            step="0.01"
            placeholder="share %"
            className={`${inputCls} w-24`}
          />
        </>
      )}
      {tab === "education" && (
        <>
          <input name="degree" required placeholder="Degree" className={inputCls} />
          <input name="specialization" placeholder="Specialization" className={inputCls} />
          <input name="institution" placeholder="Institution" className={inputCls} />
          <input name="year_completed" type="number" placeholder="Year" className={`${inputCls} w-24`} />
          <input name="grade" placeholder="Grade" className={`${inputCls} w-24`} />
        </>
      )}
      {tab === "experience" && (
        <>
          <input name="employer" required placeholder="Employer" className={inputCls} />
          <input name="designation" placeholder="Designation" className={inputCls} />
          <input name="from_date" type="date" className={inputCls} />
          <input name="to_date" type="date" className={inputCls} />
        </>
      )}
      {tab === "awards" && (
        <>
          <input name="title" required placeholder="Title" className={inputCls} />
          <input name="category" placeholder="Category" className={inputCls} />
          <input name="awarded_on" type="date" className={inputCls} />
        </>
      )}
      {tab === "training" && (
        <>
          <input name="program" required placeholder="Program" className={inputCls} />
          <input name="provider" placeholder="Provider" className={inputCls} />
          <select name="status" className={inputCls} defaultValue="planned">
            {["planned", "in_progress", "completed", "cancelled"].map((s) => (
              <option key={s} value={s}>{s.replace("_", " ")}</option>
            ))}
          </select>
          <input name="completed_on" type="date" className={inputCls} />
        </>
      )}
      {tab === "incidents" && (
        <>
          <select name="kind" className={inputCls} defaultValue="disciplinary">
            <option value="disciplinary">disciplinary</option>
            <option value="accident">accident</option>
          </select>
          <input name="incident_date" type="date" required className={inputCls} />
          <select name="severity" className={inputCls} defaultValue="low">
            {["low", "medium", "high"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <input name="description" required placeholder="Description" className={`${inputCls} min-w-48 flex-1`} />
        </>
      )}
      <button className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface">Save</button>
      <button type="button" onClick={onCancel} className="text-xs text-mute hover:text-ink">
        cancel
      </button>
    </form>
  );
}
