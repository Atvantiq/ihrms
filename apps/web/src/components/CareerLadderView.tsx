"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchCareerLadder,
  fetchCareerTracks,
  placeEmployee,
  type CareerLadder,
  type CareerTrack,
} from "@/lib/api";

export function CareerLadderView({
  employeeId,
  canPlace = false,
  title = "Career ladder",
}: {
  employeeId: number;
  canPlace?: boolean;
  title?: string;
}) {
  const [ladder, setLadder] = useState<CareerLadder | null>(null);
  const [tracks, setTracks] = useState<CareerTrack[]>([]);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchCareerLadder(employeeId).then(setLadder).catch((e) => setError(e.message));
  }, [employeeId]);
  useEffect(() => {
    reload();
    if (canPlace) fetchCareerTracks().then(setTracks).catch(() => {});
  }, [reload, canPlace]);

  async function place(levelId: string) {
    try {
      setLadder(await placeEmployee(employeeId, levelId));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  // employees with no placement and no placement control see nothing
  if (!ladder) return null;
  if (!ladder.level && !canPlace) return null;

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {canPlace && (
          <select
            value={ladder.level?.id ?? ""}
            onChange={(e) => e.target.value && place(e.target.value)}
            className="rounded-lg border border-line px-2 py-1 text-[11px]"
          >
            <option value="" disabled>Place on level…</option>
            {tracks.map((t) => (
              <optgroup key={t.id} label={t.name}>
                {t.levels.map((lv) => (
                  <option key={lv.id} value={lv.id}>L{lv.rank} · {lv.name}</option>
                ))}
              </optgroup>
            ))}
          </select>
        )}
      </div>
      {error && (
        <div className="border-b border-line bg-red-soft/30 px-4 py-2 text-xs text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}
      {ladder.level ? (
        <div className="p-4">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-indigo-soft px-2 py-0.5 text-[11px] font-semibold text-indigo-strong">
              L{ladder.level.rank}
            </span>
            <span className="text-sm font-semibold text-ink">{ladder.level.name}</span>
            <span className="text-[11px] text-mute">{ladder.track_name}</span>
            {ladder.next_level && (
              <span className="ml-auto text-[11px] text-mute">
                next → <span className="font-medium text-ink">{ladder.next_level.name}</span>
              </span>
            )}
          </div>
          {ladder.level.summary && (
            <p className="mt-1 text-[12px] text-mute">{ladder.level.summary}</p>
          )}
          {ladder.expectations.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">
                Competency expectations
              </div>
              {ladder.expectations.map((x) => (
                <div key={x.competency_id} className="text-[12px]">
                  <span className="font-medium text-ink">{x.competency_name}</span>
                  <span className="text-mute"> — {x.expectation}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="px-4 py-6 text-center text-sm text-mute">
          Not placed on a career level yet.
        </div>
      )}
    </section>
  );
}
