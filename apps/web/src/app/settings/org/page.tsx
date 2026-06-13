"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  createOrgMaster,
  fetchOrgMasters,
  mergeOrgMaster,
  renameOrgMaster,
  type OrgKind,
  type OrgMaster,
} from "@/lib/api";

const KINDS: { kind: OrgKind; label: string }[] = [
  { kind: "department", label: "Departments" },
  { kind: "division", label: "Divisions" },
  { kind: "branch", label: "Branches" },
  { kind: "designation", label: "Designations" },
];

function MasterRow({
  master,
  siblings,
  onChanged,
  onError,
}: {
  master: OrgMaster;
  siblings: OrgMaster[];
  onChanged: () => void;
  onError: (msg: string) => void;
}) {
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(master.name);
  const [mergeTarget, setMergeTarget] = useState("");

  async function saveRename() {
    if (name.trim() === master.name) {
      setRenaming(false);
      return;
    }
    try {
      await renameOrgMaster(master.id, name.trim());
      setRenaming(false);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  async function doMerge() {
    if (!mergeTarget) return;
    const target = siblings.find((s) => s.id === mergeTarget);
    if (
      !window.confirm(
        `Merge "${master.name}" into "${target?.name}"?\n\nAll ${master.employee_count} employee(s) and raw values move to "${target?.name}". This cannot be undone from the UI.`,
      )
    ) {
      setMergeTarget("");
      return;
    }
    try {
      await mergeOrgMaster(master.id, mergeTarget);
      onChanged();
    } catch (e) {
      onError((e as Error).message);
      setMergeTarget("");
    }
  }

  return (
    <tr className="border-b border-line-2 last:border-0">
      <td className="px-4 py-2">
        {renaming ? (
          <span className="flex items-center gap-1.5">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveRename()}
              autoFocus
              className="rounded-md border border-indigo bg-surface px-2 py-1 text-sm outline-none"
            />
            <button onClick={saveRename} className="text-xs text-green-strong">
              ✓
            </button>
            <button
              onClick={() => {
                setRenaming(false);
                setName(master.name);
              }}
              className="text-xs text-mute"
            >
              ✕
            </button>
          </span>
        ) : (
          <button
            onClick={() => setRenaming(true)}
            title="Click to rename"
            className="font-medium text-ink hover:text-indigo"
          >
            {master.name} <span className="text-[10px] text-mute-2">✎</span>
          </button>
        )}
      </td>
      <td className="px-3 py-2">
        <span className="flex flex-wrap gap-1">
          {master.raw_values.map((r) => (
            <span
              key={r}
              className={`rounded-md px-1.5 py-0.5 font-mono text-[10px] ${
                r === master.name
                  ? "bg-green-soft text-green-strong"
                  : "bg-line-2 text-mute"
              }`}
            >
              {r}
            </span>
          ))}
        </span>
      </td>
      <td className="px-3 py-2 text-center font-mono text-xs text-mute">
        {master.employee_count}
      </td>
      <td className="px-3 py-2 text-right">
        <select
          value={mergeTarget}
          onChange={(e) => setMergeTarget(e.target.value)}
          onBlur={doMerge}
          className="rounded-md border border-line bg-surface px-1.5 py-1 text-[11px] text-mute"
        >
          <option value="">Merge into…</option>
          {siblings
            .filter((s) => s.id !== master.id)
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
        </select>
      </td>
    </tr>
  );
}

function KindSection({
  kind,
  label,
  masters,
  onChanged,
}: {
  kind: OrgKind;
  label: string;
  masters: OrgMaster[];
  onChanged: () => void;
}) {
  const [adding, setAdding] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!adding.trim()) return;
    try {
      await createOrgMaster(kind, adding.trim());
      setAdding("");
      setError(null);
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <h2 className="text-sm font-semibold text-ink">
          {label}{" "}
          <span className="font-normal text-mute">({masters.length})</span>
        </h2>
        <form onSubmit={add} className="flex items-center gap-1.5">
          <input
            value={adding}
            onChange={(e) => setAdding(e.target.value)}
            placeholder={`Add ${kind}…`}
            className="rounded-md border border-line bg-surface px-2 py-1 text-xs outline-none placeholder:text-mute-2 focus:border-indigo"
          />
          <button
            type="submit"
            className="rounded-md bg-ink px-2 py-1 text-xs font-medium text-surface"
          >
            +
          </button>
        </form>
      </div>
      {error && (
        <div className="border-b border-line bg-red-soft/50 px-4 py-2 text-xs text-red-strong">
          {error}{" "}
          <button onClick={() => setError(null)} className="underline">
            dismiss
          </button>
        </div>
      )}
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
            <th className="px-4 py-2 font-semibold">Canonical name</th>
            <th className="px-3 py-2 font-semibold">Raw values mapped</th>
            <th className="px-3 py-2 text-center font-semibold">Employees</th>
            <th className="px-3 py-2 text-right font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody>
          {masters.map((m) => (
            <MasterRow
              key={m.id}
              master={m}
              siblings={masters}
              onChanged={onChanged}
              onError={setError}
            />
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function OrgMastersPage() {
  const [masters, setMasters] = useState<OrgMaster[]>([]);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    fetchOrgMasters()
      .then((m) => {
        setMasters(m);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(reload, [reload]);

  return (
    <div className="space-y-4">
      <div>
        <Link href="/directory" className="text-xs text-mute hover:text-ink">
          ← Back to People
        </Link>
        <h1 className="mt-1 text-xl font-semibold text-ink">Org masters</h1>
        <p className="text-xs text-mute">
          Canonical departments, divisions, branches and designations. Raw
          spellings from the legacy data are mapped underneath — rename a
          master or merge duplicates into one. ONAQT data is never rewritten.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-4 text-sm text-red-strong">
          {error}
        </div>
      )}

      {KINDS.map(({ kind, label }) => (
        <KindSection
          key={kind}
          kind={kind}
          label={label}
          masters={masters.filter((m) => m.kind === kind)}
          onChanged={reload}
        />
      ))}
    </div>
  );
}
