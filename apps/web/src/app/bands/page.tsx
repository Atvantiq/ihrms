"use client";

import { useCallback, useEffect, useState } from "react";
import { createBand, fetchBands, type Band } from "@/lib/api";

function inr(v: string | number): string {
  return "₹" + Number(v).toLocaleString("en-IN");
}

export default function BandsPage() {
  const [bands, setBands] = useState<Band[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const reload = useCallback(() => {
    fetchBands().then(setBands).catch((e) => setError(e.message));
  }, []);
  useEffect(() => reload(), [reload]);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    try {
      await createBand({
        code: fd.get("code") as string,
        name: fd.get("name") as string,
        level: Number(fd.get("level")),
        min_ctc: fd.get("min_ctc") as string,
        max_ctc: fd.get("max_ctc") as string,
      });
      form.reset();
      setShowAdd(false);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">Compensation bands</h1>
          <p className="text-xs text-mute">Salary bands by level — the comp guardrail for each grade</p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2">
          + New band
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-3 text-sm text-red-strong">
          {error} <button onClick={() => setError(null)} className="underline">dismiss</button>
        </div>
      )}

      {showAdd && (
        <form onSubmit={add} className="flex flex-wrap items-end gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm">
          <input name="code" required placeholder="Code (L6)" className="w-24 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="name" required placeholder="Name" className="min-w-40 flex-1 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="level" type="number" min="1" required placeholder="Level" className="w-20 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="min_ctc" type="number" min="1" required placeholder="Min CTC" className="w-28 rounded-lg border border-line px-3 py-2 text-sm" />
          <input name="max_ctc" type="number" min="1" required placeholder="Max CTC" className="w-28 rounded-lg border border-line px-3 py-2 text-sm" />
          <button className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface">Create</button>
        </form>
      )}

      <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
              <th className="px-4 py-2 font-semibold">Band</th>
              <th className="px-3 py-2 font-semibold">Level</th>
              <th className="px-3 py-2 font-semibold">Min CTC</th>
              <th className="px-3 py-2 font-semibold">Max CTC</th>
            </tr>
          </thead>
          <tbody>
            {bands.map((b) => (
              <tr key={b.id} className="border-b border-line-2 last:border-0">
                <td className="px-4 py-2">
                  <span className="font-mono text-[11px] text-mute">{b.code}</span>
                  <span className="ml-2 font-medium text-ink">{b.name}</span>
                </td>
                <td className="px-3 py-2 text-mute">L{b.level}</td>
                <td className="px-3 py-2 text-ink">{inr(b.min_ctc)}</td>
                <td className="px-3 py-2 text-ink">{inr(b.max_ctc)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
