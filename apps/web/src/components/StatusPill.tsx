import type { EmploymentStatus } from "@/lib/api";

const STYLES: Record<EmploymentStatus, string> = {
  Active: "bg-green-soft text-green-strong",
  Probation: "bg-warn-soft text-warn-strong",
  Joining: "bg-blue-soft text-blue-strong",
  Notice: "bg-warn-soft text-warn-strong",
  Inactive: "bg-line-2 text-mute",
};

export function StatusPill({ status }: { status: EmploymentStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${STYLES[status]}`}
    >
      ● {status}
    </span>
  );
}
