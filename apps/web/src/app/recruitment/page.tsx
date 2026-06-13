"use client";

import { useCallback, useEffect, useState } from "react";
import {
  acceptOffer,
  addCandidate,
  createRequisition,
  fetchCandidates,
  fetchRequisitions,
  makeOffer,
  moveStage,
  onboardCandidate,
  type Candidate,
  type Requisition,
} from "@/lib/api";
import { Avatar } from "@/components/Avatar";

const STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"];
const STAGE_STYLE: Record<string, string> = {
  applied: "bg-line-2 text-mute",
  screening: "bg-blue-soft text-blue-strong",
  interview: "bg-indigo-soft text-indigo-strong",
  offer: "bg-warn-soft text-warn-strong",
  hired: "bg-green-soft text-green-strong",
  rejected: "bg-red-soft text-red-strong",
};
const BGV_STYLE: Record<string, string> = {
  clear: "text-green-strong",
  flagged: "text-red-strong",
  in_progress: "text-warn-strong",
};

function CandidateRow({
  c,
  onChanged,
  onError,
}: {
  c: Candidate;
  onChanged: () => void;
  onError: (m: string) => void;
}) {
  async function advance(stage: string) {
    try {
      await moveStage(c.id, stage);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function offer() {
    const ctc = window.prompt("Annual CTC (₹)?", "1400000");
    if (!ctc) return;
    try {
      await makeOffer(c.id, {
        designation: window.prompt("Designation?", "Engineer") || "Engineer",
        department: window.prompt("Department?", "IT") || "IT",
        ctc_annual: Number(ctc),
        joining_date: window.prompt("Joining date (YYYY-MM-DD)?", "2026-07-01") || "2026-07-01",
      });
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function accept() {
    try {
      await acceptOffer(c.id);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function onboard() {
    const code = window.prompt("Employee code for the new hire?", "ATQ/NEW/001");
    if (!code) return;
    try {
      const r = await onboardCandidate(c.id, {
        employee_code: code,
        division: "Software Development",
        branch: "Main",
        circle_id: 133816249125,
      });
      onError("");
      window.alert(`Onboarded as employee ${r.employee_id}`);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  const nextStage =
    c.stage === "applied" ? "screening" : c.stage === "screening" ? "interview" : null;

  return (
    <tr className="border-b border-line-2 last:border-0">
      <td className="px-4 py-2">
        <div className="flex items-center gap-2.5">
          <Avatar name={c.name} size={28} />
          <span>
            <span className="block font-medium text-ink">{c.name}</span>
            <span className="block text-[10px] text-mute">{c.email}</span>
          </span>
        </div>
      </td>
      <td className="px-3 py-2">
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${STAGE_STYLE[c.stage]}`}
        >
          {c.stage}
        </span>
      </td>
      <td className="px-3 py-2 text-mute">{c.rating ? `${c.rating}★` : "—"}</td>
      <td className={`px-3 py-2 text-xs capitalize ${BGV_STYLE[c.bgv_status] ?? "text-mute"}`}>
        {c.bgv_status.replace("_", " ")}
      </td>
      <td className="px-3 py-2 text-right">
        <div className="flex flex-wrap justify-end gap-1.5">
          {nextStage && (
            <button onClick={() => advance(nextStage)} className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-ink">
              → {nextStage}
            </button>
          )}
          {c.stage === "interview" && (
            <button onClick={offer} className="rounded-md bg-warn-soft px-2 py-1 text-[11px] font-medium text-warn-strong">
              Make offer
            </button>
          )}
          {c.stage === "offer" && (
            <>
              <button onClick={accept} className="rounded-md bg-blue-soft px-2 py-1 text-[11px] font-medium text-blue-strong">
                Accept
              </button>
              <button onClick={onboard} className="rounded-md bg-green-soft px-2 py-1 text-[11px] font-medium text-green-strong">
                Onboard
              </button>
            </>
          )}
          {!["hired", "rejected"].includes(c.stage) && (
            <button onClick={() => advance("rejected")} className="rounded-md border border-line px-2 py-1 text-[11px] text-mute hover:text-red-strong">
              Reject
            </button>
          )}
          {c.onboarded_employee_id && (
            <span className="rounded-md bg-green-soft px-2 py-1 text-[11px] text-green-strong">
              ✓ Emp {c.onboarded_employee_id}
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}

export default function RecruitmentPage() {
  const [reqs, setReqs] = useState<Requisition[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showReq, setShowReq] = useState(false);

  const reloadReqs = useCallback(() => {
    fetchRequisitions().then(setReqs).catch((e) => setError(e.message));
  }, []);
  useEffect(reloadReqs, [reloadReqs]);

  const reloadCands = useCallback(() => {
    if (selected) fetchCandidates(selected).then(setCandidates).catch(() => {});
  }, [selected]);
  useEffect(reloadCands, [reloadCands]);

  async function addReq(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await createRequisition({
        code: fd.get("code") as string,
        title: fd.get("title") as string,
        department: (fd.get("department") as string) || undefined,
        location: (fd.get("location") as string) || undefined,
        openings: Number(fd.get("openings")) || 1,
      });
      setShowReq(false);
      reloadReqs();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addCand(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selected) return;
    const fd = new FormData(e.currentTarget);
    try {
      await addCandidate({
        requisition_id: selected,
        name: fd.get("name") as string,
        email: fd.get("email") as string,
        phone: (fd.get("phone") as string) || undefined,
      });
      (e.target as HTMLFormElement).reset();
      reloadCands();
      reloadReqs();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const sel = reqs.find((r) => r.id === selected);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Recruitment</h1>
          <p className="text-xs text-mute">
            Requisitions → pipeline → offer → onboard (creates a real employee)
          </p>
        </div>
        <button
          onClick={() => setShowReq(!showReq)}
          className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2"
        >
          + New requisition
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {showReq && (
        <form onSubmit={addReq} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <input name="code" required placeholder="REQ-CODE" className="rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="title" required placeholder="Job title" className="flex-1 min-w-40 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="department" placeholder="Department" className="rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="location" placeholder="Location" className="rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="openings" type="number" min={1} defaultValue={1} className="w-20 rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Create</button>
        </form>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
            Requisitions <span className="font-normal text-mute">({reqs.length})</span>
          </div>
          <div className="divide-y divide-line-2">
            {reqs.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelected(r.id)}
                className={`flex w-full items-center justify-between px-4 py-2.5 text-left text-sm hover:bg-line-2/50 ${
                  selected === r.id ? "bg-indigo-soft/40" : ""
                }`}
              >
                <span>
                  <span className="block font-medium text-ink">{r.title}</span>
                  <span className="block text-[10px] text-mute">
                    {r.code} · {r.department ?? "—"} · {r.openings} opening(s)
                  </span>
                </span>
                <span className="rounded-full bg-line-2 px-2 py-0.5 text-[10px] text-mute">
                  {r.candidate_count}
                </span>
              </button>
            ))}
            {reqs.length === 0 && (
              <div className="px-4 py-6 text-center text-sm text-mute">
                No requisitions yet.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-line bg-surface shadow-sm lg:col-span-2">
          {sel ? (
            <>
              <div className="border-b border-line px-4 py-2.5">
                <div className="text-sm font-semibold text-ink">{sel.title}</div>
                <div className="text-[10px] text-mute">Pipeline · {candidates.length} candidate(s)</div>
              </div>
              <form onSubmit={addCand} className="flex flex-wrap items-end gap-2 border-b border-line bg-canvas px-4 py-2.5">
                <input name="name" required placeholder="Candidate name" className="flex-1 min-w-32 rounded-lg border border-line px-3 py-1.5 text-sm" />
                <input name="email" type="email" required placeholder="email" className="rounded-lg border border-line px-3 py-1.5 text-sm" />
                <input name="phone" placeholder="phone" className="w-32 rounded-lg border border-line px-3 py-1.5 text-sm" />
                <button className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface">+ Add</button>
              </form>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
                    <th className="px-4 py-2 font-semibold">Candidate</th>
                    <th className="px-3 py-2 font-semibold">Stage</th>
                    <th className="px-3 py-2 font-semibold">Rating</th>
                    <th className="px-3 py-2 font-semibold">BGV</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {STAGES.flatMap((s) => candidates.filter((c) => c.stage === s)).map((c) => (
                    <CandidateRow key={c.id} c={c} onChanged={() => { reloadCands(); reloadReqs(); }} onError={setError} />
                  ))}
                  {candidates.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-6 text-center text-mute">
                        No candidates yet — add one above.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </>
          ) : (
            <div className="flex h-40 items-center justify-center text-sm text-mute">
              Select a requisition to see its pipeline.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
