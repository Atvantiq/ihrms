"use client";

import { useCallback, useEffect, useState } from "react";
import {
  addCareerLevel,
  createCareerTrack,
  createCompetency,
  fetchCareerTracks,
  fetchCompetencies,
  fetchLevelExpectations,
  setLevelExpectation,
  type CareerTrack,
  type Competency,
  type LevelExpectation,
} from "@/lib/api";

function LevelExpectations({
  levelId,
  competencies,
  onError,
}: {
  levelId: string;
  competencies: Competency[];
  onError: (m: string) => void;
}) {
  const [exps, setExps] = useState<LevelExpectation[]>([]);
  const reload = useCallback(() => {
    fetchLevelExpectations(levelId).then(setExps).catch((e) => onError(e.message));
  }, [levelId, onError]);
  useEffect(() => reload(), [reload]);

  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const cid = fd.get("competency_id") as string;
    const exp = (fd.get("expectation") as string).trim();
    if (!cid || !exp) return;
    try {
      setExps(await setLevelExpectation(levelId, cid, exp));
      form.reset();
    } catch (err) {
      onError((err as Error).message);
    }
  }

  return (
    <div className="mt-1.5 space-y-1 pl-4">
      {exps.map((x) => (
        <div key={x.competency_id} className="text-[11px] text-mute">
          <span className="font-medium text-ink">{x.competency_name}:</span> {x.expectation}
        </div>
      ))}
      <form onSubmit={save} className="flex flex-wrap gap-1.5 pt-1">
        <select name="competency_id" defaultValue="" className="rounded-lg border border-line px-2 py-1 text-[11px]">
          <option value="" disabled>competency…</option>
          {competencies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input name="expectation" placeholder="Expectation at this level" className="min-w-48 flex-1 rounded-lg border border-line px-2 py-1 text-[11px]" />
        <button className="rounded-lg border border-line px-2 py-1 text-[11px] text-mute hover:text-ink">Set</button>
      </form>
    </div>
  );
}

export default function CareerPage() {
  const [tracks, setTracks] = useState<CareerTrack[]>([]);
  const [competencies, setCompetencies] = useState<Competency[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [addingLevel, setAddingLevel] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchCareerTracks().then(setTracks).catch((e) => setError(e.message));
    fetchCompetencies().then(setCompetencies).catch((e) => setError(e.message));
  }, []);
  useEffect(() => reload(), [reload]);

  async function addTrack(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await createCareerTrack(fd.get("name") as string, (fd.get("description") as string) || undefined);
      form.reset();
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addLevel(trackId: string, e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await addCareerLevel(trackId, {
        name: fd.get("name") as string,
        rank: Number(fd.get("rank")),
        summary: (fd.get("summary") as string) || null,
      });
      form.reset();
      setAddingLevel(null);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addCompetency(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await createCompetency({
        name: fd.get("name") as string,
        category: (fd.get("category") as string) || null,
      });
      form.reset();
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-ink">Career ladders</h1>
        <p className="text-xs text-mute">Tracks · levels · competency framework · per-level expectations</p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.7fr_1fr]">
        <div className="space-y-4">
          {tracks.map((t) => (
            <section key={t.id} className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
              <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
                <div>
                  <span className="text-sm font-semibold text-ink">{t.name}</span>
                  {t.description && <span className="ml-2 text-[11px] text-mute">{t.description}</span>}
                </div>
                <button
                  onClick={() => setAddingLevel(addingLevel === t.id ? null : t.id)}
                  className="text-[11px] text-blue-strong hover:underline"
                >
                  {addingLevel === t.id ? "Cancel" : "+ level"}
                </button>
              </div>
              {addingLevel === t.id && (
                <form onSubmit={(e) => addLevel(t.id, e)} className="flex flex-wrap items-end gap-2 border-b border-line bg-canvas p-3">
                  <input name="name" required placeholder="Level name" className="rounded-lg border border-line px-2 py-1.5 text-sm" />
                  <input name="rank" type="number" min="1" required placeholder="Rank" className="w-20 rounded-lg border border-line px-2 py-1.5 text-sm" />
                  <input name="summary" placeholder="Summary" className="min-w-40 flex-1 rounded-lg border border-line px-2 py-1.5 text-sm" />
                  <button className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface">Add</button>
                </form>
              )}
              <div className="divide-y divide-line-2">
                {t.levels.map((lv) => (
                  <div key={lv.id} className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-indigo-soft px-1.5 py-0.5 text-[10px] font-semibold text-indigo-strong">
                        L{lv.rank}
                      </span>
                      <span className="text-sm font-medium text-ink">{lv.name}</span>
                      {lv.summary && <span className="text-[11px] text-mute">{lv.summary}</span>}
                    </div>
                    <LevelExpectations levelId={lv.id} competencies={competencies} onError={setError} />
                  </div>
                ))}
                {t.levels.length === 0 && (
                  <div className="px-4 py-4 text-sm text-mute">No levels yet.</div>
                )}
              </div>
            </section>
          ))}

          <form onSubmit={addTrack} className="flex flex-wrap items-end gap-2 rounded-xl border border-line bg-surface p-4 shadow-sm">
            <input name="name" required placeholder="New track name" className="rounded-lg border border-line px-3 py-2 text-sm" />
            <input name="description" placeholder="Description" className="min-w-40 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
            <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">+ Track</button>
          </form>
        </div>

        <section className="h-fit overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <div className="border-b border-line px-4 py-2.5 text-sm font-semibold text-ink">
            Competency framework <span className="font-normal text-mute">({competencies.length})</span>
          </div>
          <div className="divide-y divide-line-2">
            {competencies.map((c) => (
              <div key={c.id} className="px-4 py-2 text-sm">
                <span className="font-medium text-ink">{c.name}</span>
                {c.category && (
                  <span className="ml-2 rounded-full bg-line-2 px-1.5 py-0.5 text-[10px] text-mute">{c.category}</span>
                )}
              </div>
            ))}
          </div>
          <form onSubmit={addCompetency} className="flex flex-wrap items-end gap-2 border-t border-line p-3">
            <input name="name" required placeholder="Competency" className="flex-1 rounded-lg border border-line px-2 py-1.5 text-sm" />
            <input name="category" placeholder="Category" className="w-24 rounded-lg border border-line px-2 py-1.5 text-sm" />
            <button className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface">Add</button>
          </form>
        </section>
      </div>
    </div>
  );
}
