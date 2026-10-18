"use client";
import { Button } from "@/components/ui/button";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

// "Run evals" for the demo. A run costs money, so it starts only on click + confirmation; the
// backend also allows one run at a time and enforces a cooldown between runs.

interface Status {
  running: boolean;
  done: number;
  total: number;
  current: string | null;
  error: string | null;
  cooldown_s: number;
  cooldown_min: number;
  scenarios: number;
  provider: string;
  estimate: string;
  llm_configured: boolean;
}

export function RunEvals() {
  const router = useRouter();
  const [status, setStatus] = useState<Status | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [judge, setJudge] = useState(true);
  const [starting, setStarting] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch("/api/evals/status", { cache: "no-store" });
      const body = await r.json();
      if (r.ok) setStatus(body);
      else setMessage(body.message ?? "The backend is not reachable.");
      return r.ok ? (body as Status) : null;
    } catch {
      setMessage("The backend is not reachable.");
      return null;
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll only while a run is in progress; reload the results when it finishes.
  useEffect(() => {
    if (!status?.running) return;
    const t = setInterval(async () => {
      const s = await refresh();
      if (s && !s.running) {
        setMessage(s.error ? `The run failed: ${s.error}` : "Run finished. Results updated.");
        router.refresh();
      }
    }, 3000);
    return () => clearInterval(t);
  }, [status?.running, refresh, router]);

  async function start() {
    if (!status) return;
    const what = judge ? "the live pipeline and the judge model" : "the live pipeline (no judge model)";
    if (!window.confirm(`Run all ${status.scenarios} scenarios through ${what} on ${status.provider}?\n\nTakes 3–5 minutes and costs ${status.estimate}.`)) return;
    setStarting(true);
    setMessage(null);
    try {
      const r = await fetch("/api/evals/run", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ judge }) });
      const body = await r.json();
      if (!r.ok) setMessage(body.message ?? "The run could not be started.");
      if (body.running !== undefined) setStatus(body);
    } finally {
      setStarting(false);
    }
  }

  const cooling = (status?.cooldown_s ?? 0) > 0;
  const disabled = !status || status.running || starting || cooling || !status.llm_configured;

  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={start} disabled={disabled}>
          {status?.running ? `Running… ${status.done}/${status.total}` : "Run evals"}
        </Button>
        <label className="flex items-center gap-1.5 text-sm text-ink-2">
          <input type="checkbox" checked={judge} onChange={(e) => setJudge(e.target.checked)} disabled={status?.running} />
          with judge model
        </label>
        <span className="text-xs text-ink-3">
          {!status
            ? "Checking the backend…"
            : status.running
              ? `Scoring ${status.current ?? "…"}`
              : cooling
                ? `Next run available in ${Math.ceil(status.cooldown_s / 60)} min (one run per ${status.cooldown_min} min)`
                : `${status.scenarios} scenarios · ${status.provider} · ${status.estimate}`}
        </span>
      </div>
      {status?.running && (
        <progress
          value={status.done}
          max={Math.max(status.total, 1)}
          aria-label="Eval run progress"
          className="mt-3 block h-1.5 w-full overflow-hidden rounded [&::-moz-progress-bar]:bg-accent [&::-webkit-progress-bar]:bg-line [&::-webkit-progress-value]:bg-accent"
        />
      )}
      <p className="mt-2 text-sm text-ink-2" aria-live="polite">{message}</p>
    </div>
  );
}
