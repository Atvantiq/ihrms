"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const devLoginEnabled = process.env.NEXT_PUBLIC_DEV_LOGIN === "true";

  async function signIn(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error } = await supabase().auth.signInWithPassword({
      email,
      password,
    });
    setBusy(false);
    if (error) {
      setError(error.message);
      return;
    }
    router.push("/dashboard");
  }

  async function devSignIn() {
    setBusy(true);
    setError(null);
    try {
      const apiBase =
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
      const res = await fetch(`${apiBase}/auth/dev-login`, { method: "POST" });
      if (!res.ok) throw new Error(`Dev login unavailable (${res.status})`);
      const s = await res.json();
      const { error } = await supabase().auth.setSession({
        access_token: s.access_token,
        refresh_token: s.refresh_token,
      });
      if (error) throw error;
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-8 shadow-md">
        <div className="ai-gradient mx-auto mb-4 h-11 w-11 rounded-xl" />
        <h1 className="text-center text-lg font-semibold text-ink">
          Atvantiq People
        </h1>
        <p className="mb-6 text-center text-xs text-mute">
          Sign in with your work account
        </p>

        <form onSubmit={signIn} className="space-y-3">
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@atvantiq.com"
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none placeholder:text-mute-2 focus:border-indigo"
            />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-mute">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none placeholder:text-mute-2 focus:border-indigo"
            />
          </div>

          {error && (
            <div className="rounded-lg bg-red-soft px-3 py-2 text-xs text-red-strong">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-ink py-2 text-sm font-medium text-surface hover:bg-ink-2 disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {devLoginEnabled && (
          <>
            <div className="my-4 flex items-center gap-2 text-[10px] uppercase tracking-wider text-mute-2">
              <span className="h-px flex-1 bg-line" /> or{" "}
              <span className="h-px flex-1 bg-line" />
            </div>
            <button
              onClick={devSignIn}
              disabled={busy}
              className="w-full rounded-lg border border-dashed border-indigo bg-indigo-soft py-2 text-sm font-medium text-indigo-strong hover:opacity-80 disabled:opacity-50"
            >
              ⚡ Dev sign-in as HR (localhost)
            </button>
          </>
        )}

        <p className="mt-4 text-center text-[11px] text-mute-2">
          Same login as ONAQT · contact your administrator for access
        </p>
      </div>
    </main>
  );
}
