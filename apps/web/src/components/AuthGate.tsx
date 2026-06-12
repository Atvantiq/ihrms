"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

/** Client-side guard: renders children only with an active Supabase session. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    supabase()
      .auth.getSession()
      .then(({ data }) => {
        if (!data.session) {
          router.replace("/login");
        } else {
          setEmail(data.session.user.email ?? null);
          setReady(true);
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
    <>
      <header className="flex items-center justify-between border-b border-line bg-surface px-6 py-2.5">
        <div className="flex items-center gap-2">
          <div className="ai-gradient h-6 w-6 rounded-md" />
          <span className="text-sm font-semibold text-ink">
            Atvantiq People
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-mute">{email}</span>
          <button
            onClick={signOut}
            className="rounded-lg border border-line px-2.5 py-1 text-xs text-mute hover:text-ink"
          >
            Sign out
          </button>
        </div>
      </header>
      {children}
    </>
  );
}
