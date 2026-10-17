import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";
import { z } from "zod";
import { Report } from "@/lib/report";
import { referenceAnswers } from "@/data/reference-answers";

// Resolution order:
// 1. ASSESS_BACKEND_URL set → forward the enquiry to the pipeline (live).
// 2. outputs/<scenarioId>.json from the batch runner → cached.
// 3. Organizer worked example (D01, D02) → reference.
// Otherwise 503, so the UI never shows a made-up answer.

const Body = z.object({ enquiry: z.string().min(1).max(8000), scenarioId: z.string().optional() });
const OUTPUTS_DIR = path.join(process.cwd(), "outputs");

export async function POST(req: Request) {
  const parsed = Body.safeParse(await req.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  const { enquiry, scenarioId } = parsed.data;

  const backend = process.env.ASSESS_BACKEND_URL;
  if (backend) {
    try {
      const r = await fetch(backend, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ enquiry, scenarioId }),
        signal: AbortSignal.timeout(90_000),
      });
      const report = Report.safeParse(await r.json());
      if (r.ok && report.success) return NextResponse.json({ ...report.data, origin: "live" });
      console.error("assess backend returned an invalid report", report.error?.issues);
    } catch (e) {
      console.error("assess backend unreachable", e);
    }
  }

  if (scenarioId && /^[A-Z]\d{2}$/.test(scenarioId)) {
    try {
      const raw = await fs.readFile(path.join(OUTPUTS_DIR, `${scenarioId}.json`), "utf8");
      const report = Report.safeParse(JSON.parse(raw));
      if (report.success) return NextResponse.json({ ...report.data, origin: "cached" });
    } catch {
      // no cached output for this scenario
    }
    const ref = referenceAnswers[scenarioId];
    if (ref) return NextResponse.json(ref);
  }

  return NextResponse.json(
    {
      error: "pipeline_not_connected",
      message: backend
        ? "The assessment pipeline did not return a valid report."
        : "No assessment pipeline is connected and no cached output exists for this enquiry.",
    },
    { status: 503 },
  );
}
