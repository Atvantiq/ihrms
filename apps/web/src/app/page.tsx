import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <div className="w-full max-w-md rounded-2xl bg-surface shadow-md border border-line p-8 text-center">
        <div className="ai-gradient mx-auto mb-4 h-12 w-12 rounded-xl" />
        <h1 className="text-xl font-semibold text-ink">Atvantiq People</h1>
        <p className="mt-1 text-mute">iHRMS — hire to retire, one platform</p>
        <div className="mt-6 flex justify-center gap-2 text-xs">
          <span className="rounded-md bg-green-soft px-2 py-1 font-medium text-green-strong">
            Web scaffold ready
          </span>
          <span className="rounded-md bg-indigo-soft px-2 py-1 font-medium text-indigo-strong">
            Prism tokens loaded
          </span>
        </div>
        <div className="mt-6">
          <Link
            href="/directory"
            className="inline-block rounded-lg bg-ink px-4 py-2 text-sm font-medium text-surface hover:bg-ink-2"
          >
            Open People directory →
          </Link>
        </div>
      </div>
    </main>
  );
}
