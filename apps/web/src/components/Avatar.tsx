const COLORS = [
  "bg-indigo-soft text-indigo-strong",
  "bg-green-soft text-green-strong",
  "bg-blue-soft text-blue-strong",
  "bg-pink-soft text-pink-strong",
  "bg-warn-soft text-warn-strong",
];

export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "?";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  // stable color per name
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) | 0;
  const color = COLORS[Math.abs(hash) % COLORS.length];
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-full font-semibold ${color}`}
      style={{ width: size, height: size, fontSize: size * 0.34 }}
    >
      {initialsOf(name)}
    </div>
  );
}
