"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  fetchEmployees,
  fetchMe,
  type EmployeeListOut,
} from "@/lib/api";
import { Avatar } from "@/components/Avatar";
import { StatusPill } from "@/components/StatusPill";

const STATUSES = ["Active", "Probation", "Joining", "Notice", "Inactive"];

function StatTile({
  label,
  value,
  hint,
  valueClass,
}: {
  label: string;
  value: number;
  hint: string;
  valueClass: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-mute">
        {label}
      </div>
      <div className={`text-[22px] font-semibold ${valueClass}`}>{value}</div>
      <div className="text-[10px] text-mute-2">{hint}</div>
    </div>
  );
}

export default function DirectoryPage() {
  const [data, setData] = useState<EmployeeListOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [department, setDepartment] = useState("");
  const [status, setStatus] = useState("");
  const [isHr, setIsHr] = useState(false);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 25;

  useEffect(() => {
    fetchMe()
      .then((me) => setIsHr(me.is_hr))
      .catch(() => {});
  }, []);

  // debounce the search input
  const [debouncedQ, setDebouncedQ] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 250);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    fetchEmployees({
      q: debouncedQ,
      department,
      status,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    })
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [debouncedQ, department, status, page]);

  const stats = data?.stats;
  const departments = useMemo(() => stats?.departments ?? [], [stats]);
  const totalMatches = data?.total_matches ?? 0;
  const pageCount = Math.max(1, Math.ceil(totalMatches / PAGE_SIZE));

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 p-6">
      {/* Page head */}
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">People</h1>
          <p className="text-xs text-mute">
            {stats
              ? `${data?.total_matches} of ${stats.total} employees · ${departments.length} departments`
              : "Loading directory…"}
          </p>
        </div>
        {isHr && (
          <Link
            href="/directory/new"
            className="rounded-lg bg-ink px-3 py-1.5 text-xs font-medium text-surface hover:bg-ink-2"
          >
            + Add employee
          </Link>
        )}
      </div>

      {/* Filter bar */}
      <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-line bg-surface p-3 shadow-sm">
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(0);
          }}
          placeholder="Search by name, ID, email…"
          className="min-w-60 flex-1 max-w-85 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm outline-none placeholder:text-mute-2 focus:border-indigo"
        />
        <span className="ml-1 text-[10px] font-semibold uppercase tracking-wider text-mute">
          Filter:
        </span>
        <select
          value={department}
          onChange={(e) => {
            setDepartment(e.target.value);
            setPage(0);
          }}
          className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-ink"
        >
          <option value="">All departments</option>
          {departments.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(0);
          }}
          className="rounded-lg border border-line bg-surface px-2 py-1.5 text-sm text-ink"
        >
          <option value="">All status</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <div className="flex-1" />
        <span className="text-[10px] text-mute">
          {data ? `${data.total_matches} matches` : "…"}
        </span>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-5">
          <StatTile label="Active" value={stats.active} hint="past probation" valueClass="text-green" />
          <StatTile label="Probation" value={stats.probation} hint="first 90 days" valueClass="text-warn" />
          <StatTile label="Joining" value={stats.joining} hint="DoJ in future" valueClass="text-indigo" />
          <StatTile label="On notice" value={stats.notice} hint="resigned · serving" valueClass="text-warn" />
          <StatTile label="Inactive" value={stats.inactive} hint="left · disabled" valueClass="text-mute" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-soft bg-red-soft/50 p-4 text-sm text-red-strong">
          Could not reach the API — is it running on port 8000? <br />
          <span className="font-mono text-xs">{error}</span>
        </div>
      )}

      {/* Employee table */}
      {data && (
        <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-sm">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-line text-[10px] uppercase tracking-wider text-mute">
                <th className="px-4 py-2.5 font-semibold">Employee</th>
                <th className="px-3 py-2.5 font-semibold">Emp ID</th>
                <th className="px-3 py-2.5 font-semibold">Designation</th>
                <th className="px-3 py-2.5 font-semibold">Department</th>
                <th className="px-3 py-2.5 font-semibold">Branch</th>
                <th className="px-3 py-2.5 font-semibold">Manager</th>
                <th className="px-3 py-2.5 font-semibold">Tenure</th>
                <th className="px-3 py-2.5 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((e) => (
                <tr
                  key={e.employee_id}
                  className="border-b border-line-2 last:border-0 hover:bg-line-2/50"
                >
                  <td className="px-4 py-2">
                    <Link
                      href={`/directory/${e.employee_id}`}
                      className="flex items-center gap-2.5"
                    >
                      <Avatar name={e.full_name} size={30} />
                      <span>
                        <span className="block font-medium text-ink">
                          {e.full_name}
                        </span>
                        <span className="block text-[10px] text-mute">
                          {e.email}
                        </span>
                      </span>
                    </Link>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-mute">
                    {e.employee_code}
                  </td>
                  <td className="px-3 py-2 text-ink">{e.designation ?? "—"}</td>
                  <td className="px-3 py-2 text-mute">{e.department ?? "—"}</td>
                  <td className="px-3 py-2 text-mute">{e.branch ?? "—"}</td>
                  <td className="px-3 py-2 text-mute">{e.manager_name ?? "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs text-mute">
                    {e.tenure}
                  </td>
                  <td className="px-3 py-2">
                    <StatusPill status={e.status} />
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-mute">
                    No employees match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          {totalMatches > 0 && (
            <div className="flex items-center justify-between border-t border-line px-4 py-2.5 text-xs text-mute">
              <span>
                Showing {page * PAGE_SIZE + 1}–
                {Math.min((page + 1) * PAGE_SIZE, totalMatches)} of{" "}
                {totalMatches}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[11px]">
                  Page {page + 1} of {pageCount}
                </span>
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="rounded-md border border-line px-2 py-1 text-mute hover:text-ink disabled:opacity-40"
                  aria-label="Previous page"
                >
                  ‹
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                  disabled={page >= pageCount - 1}
                  className="rounded-md border border-line px-2 py-1 text-mute hover:text-ink disabled:opacity-40"
                  aria-label="Next page"
                >
                  ›
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
