"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchMe } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { supabase } from "@/lib/supabase";

/** Client-side guard + app shell: renders the sidebar + topbar around
 *  authenticated pages, redirecting to /login without a session. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState<string | null>(null);
  const [isHr, setIsHr] = useState(false);
  const [persona, setPersona] = useState("employee");

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
            .then((me) => {
              setIsHr(me.is_hr);
              setPersona(me.persona);
            })
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
        <Topbar email={email} persona={persona} onSignOut={signOut} />
        {/* Standard content canvas — the SINGLE source of truth for content
            width + padding (prototype `.canvas`: full-width 1fr, padding
            18/22px). Pages must NOT set their own mx-auto/max-w/padding. */}
        <main className="flex-1 overflow-y-auto px-6 py-5">{children}</main>
      </div>
    </div>
  );
}
