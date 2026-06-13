"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/components/nav";

export function Sidebar({ isHr, isSuper }: { isHr: boolean; isSuper: boolean }) {
  const pathname = usePathname();

  return (
    <aside className="flex w-[220px] shrink-0 flex-col border-r border-line bg-surface">
      <div className="flex items-center gap-2.5 px-4 py-3.5">
        <div className="ai-gradient h-[26px] w-[26px] rounded-[7px]" />
        <div className="leading-tight">
          <div className="text-sm font-medium tracking-tight text-ink">
            Atvantiq <span className="text-mute">/</span> People
          </div>
          <div className="text-[10px] tracking-wide text-mute">v1.0 · India</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-4">
        {NAV.map((section) => {
          const items = section.items.filter(
            (i) => (!i.hrOnly || isHr) && (!i.superOnly || isSuper),
          );
          if (items.length === 0) return null;
          return (
            <div key={section.label} className="mb-3">
              <div className="px-2 py-1 text-[9px] font-semibold uppercase tracking-wider text-mute-2">
                {section.label}
              </div>
              {items.map((item) => {
                const active =
                  pathname === item.href ||
                  pathname.startsWith(item.href + "/");
                if (item.comingSoon) {
                  return (
                    <div
                      key={item.href}
                      title="Coming soon"
                      className="flex cursor-default items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm text-mute-2"
                    >
                      <span className="w-4 text-center">{item.icon}</span>
                      <span className="flex-1">{item.label}</span>
                      <span className="rounded bg-line-2 px-1 py-0.5 text-[8px] font-semibold uppercase text-mute-2">
                        soon
                      </span>
                    </div>
                  );
                }
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm transition-colors ${
                      active
                        ? "bg-indigo-soft font-medium text-indigo-strong"
                        : "text-ink-2 hover:bg-line-2"
                    }`}
                  >
                    <span className="w-4 text-center">{item.icon}</span>
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
