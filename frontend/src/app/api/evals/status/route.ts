import { forward } from "../backend";

export const dynamic = "force-dynamic";

export async function GET() {
  return forward("/evals/status");
}
