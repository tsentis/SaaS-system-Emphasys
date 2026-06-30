async function getApiHealth(): Promise<string> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}/api/v1/health`, { cache: "no-store" });
    if (!res.ok) return "unreachable";
    const data = await res.json();
    return `ok (v${data.version})`;
  } catch {
    return "unreachable";
  }
}

export default async function Home() {
  const apiStatus = await getApiHealth();

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-6 px-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-widest text-blue-600">
          Emphasys Centre
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">
          European Project Intelligence Platform
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          AI-powered analysis of European project proposals — Erasmus+, Horizon
          Europe, CERV, Interreg, AMIF, Digital Europe and more.
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-500">Backend API status</span>
          <span className="font-mono text-sm font-semibold text-slate-800">
            {apiStatus}
          </span>
        </div>
      </div>

      <p className="text-sm text-slate-400">
        Milestone 0 — scaffolding. Authentication, upload, and analysis arrive in
        the next milestones.
      </p>
    </main>
  );
}
