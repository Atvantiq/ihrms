"use client";

import { Avatar } from "@/components/Avatar";

const PERSONA_LABEL: Record<string, string> = {
  hr: "HR Admin",
  employee: "Employee",
  manager: "Manager",
  super: "Platform Owner",
};

export function Topbar({
  email,
  persona,
  onSignOut,
}: {
  email: string | null;
  persona: string;
  onSignOut: () => void;
}) {
  return (
    <header className="flex items-center gap-3 border-b border-line bg-surface px-4 py-2">
      {/* Persona chip (reflects the signed-in user's resolved persona) */}
      <span className="flex items-center gap-1.5 rounded-full border border-line bg-canvas px-2.5 py-1 text-xs text-ink-2">
        <span className="h-1.5 w-1.5 rounded-full bg-green" />
        {PERSONA_LABEL[persona] ?? "Employee"}
      </span>

      {/* Command search — styled to the prototype; AI smart-search is a
          future module, so this is a non-functional placeholder for now. */}
      <button
        type="button"
        title="AI smart search — coming soon"
        className="flex max-w-md flex-1 items-center gap-2 rounded-lg border border-line bg-canvas px-3 py-1.5 text-left text-xs text-mute-2 hover:border-indigo/40"
      >
        <span className="bg-gradient-to-br from-indigo via-magenta to-amber bg-clip-text text-transparent">
          ✦
        </span>
        <span className="flex-1 truncate">
          Ask anything · “show probation ending this month”
        </span>
        <kbd className="rounded border border-line bg-surface px-1.5 py-0.5 font-mono text-[10px] text-mute">
          ⌘K
        </kbd>
      </button>

      <div className="flex items-center gap-3">
        <button
          type="button"
          title="Notifications — coming soon"
          className="text-mute hover:text-ink"
        >
          🔔
        </button>
        <div className="flex items-center gap-2">
          {email && <Avatar name={email} size={26} />}
          <span className="hidden text-xs text-mute sm:inline">{email}</span>
        </div>
        <button
          onClick={onSignOut}
          className="rounded-lg border border-line px-2.5 py-1 text-xs text-mute hover:text-ink"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
