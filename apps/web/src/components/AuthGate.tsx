"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { supabase } from "@/lib/supabase";

/** Client-side guard + app shell: renders the sidebar + topbar around
 *  authenticated pages, redirecting to /login without a session. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState<string | null>(null);
  const [isHr, setIsHr] = useState(false);

  useEffect(() => {
    supabase()
      .auth.getSession()
      .then(({ data }) => {
        if (!data.session) {
          router.replace("/login");
        } else {
          setEmail(data.session.user.email ?? null);
          setReady(true);
          fetchMe()
            .then((me) => setIsHr(me.is_hr))
            .catch(() => {});
        }
      });
  }, [router]);

  async function signOut() {
    await supabase().auth.signOut();
    router.replace("/login");
  }

  if (!ready)
    return (
      <main className="flex flex-1 items-center justify-center p-8 text-sm text-mute">
        Checking session…
      </main>
    );

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar isHr={isHr} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-end border-b border-line bg-surface px-6 py-2.5">
          <div className="flex items-center gap-3">
            <span className="text-xs text-mute">{email}</span>
            {isHr && (
              <span className="rounded bg-indigo-soft px-1.5 py-0.5 text-[9px] font-semibold uppercase text-indigo-strong">
                HR
              </span>
            )}
            <button
              onClick={signOut}
              className="rounded-lg border border-line px-2.5 py-1 text-xs text-mute hover:text-ink"
            >
              Sign out
            </button>
          </div>
        </header>
        {/* Standard content canvas — the SINGLE source of truth for content
            width + padding (prototype `.canvas`: full-width 1fr, padding
            18/22px). Pages must NOT set their own mx-auto/max-w/padding. */}
        <main className="flex-1 overflow-y-auto px-6 py-5">{children}</main>
      </div>
    </div>
  );
}
