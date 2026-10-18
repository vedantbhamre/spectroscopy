import { NextResponse } from "next/server";

// The FastAPI base URL: EVALS_BACKEND_URL, else ASSESS_BACKEND_URL without its /assess path.
export function backendBase(): string | null {
  const explicit = process.env.EVALS_BACKEND_URL;
  if (explicit) return explicit.replace(/\/$/, "");
  const assess = process.env.ASSESS_BACKEND_URL;
  return assess ? assess.replace(/\/assess\/?$/, "") : null;
}

export async function forward(path: string, init?: RequestInit) {
  const base = backendBase();
  if (!base) return NextResponse.json({ error: "not_connected", message: "No backend is configured (ASSESS_BACKEND_URL)." }, { status: 503 });
  try {
    const r = await fetch(`${base}${path}`, { ...init, cache: "no-store", signal: AbortSignal.timeout(15_000) });
    return NextResponse.json(await r.json(), { status: r.status });
  } catch {
    return NextResponse.json({ error: "unreachable", message: "The backend did not respond. Is the FastAPI server running?" }, { status: 503 });
  }
}
