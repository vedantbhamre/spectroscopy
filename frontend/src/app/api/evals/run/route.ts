import { forward } from "../backend";

// Starts a paid eval run on the backend. Only the Evals page's button calls this, after a confirmation.
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  return forward("/evals/run", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ judge: body?.judge !== false }),
  });
}
