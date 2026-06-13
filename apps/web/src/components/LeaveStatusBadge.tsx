const STYLES: Record<string, string> = {
  pending: "bg-warn-soft text-warn-strong",
  approved: "bg-green-soft text-green-strong",
  rejected: "bg-red-soft text-red-strong",
  cancelled: "bg-line-2 text-mute",
};

export function LeaveStatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${
        STYLES[status] ?? "bg-line-2 text-mute"
      }`}
    >
      ● {status}
    </span>
  );
}
