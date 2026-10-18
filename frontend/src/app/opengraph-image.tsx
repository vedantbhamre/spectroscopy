import { ImageResponse } from "next/og";
import { SITE } from "@/lib/site";

export const alt = SITE.title;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Social preview in the site's system: white canvas, light display type, the spectrum rule.
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#ffffff", padding: 72 }}>
        <div style={{ fontSize: 30, color: "#525252" }}>In-line spectroscopy · Art Fiber Systems</div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 76, fontWeight: 300, color: "#161616", lineHeight: 1.1, maxWidth: 980 }}>Turn a customer enquiry into a cited spectroscopy assessment</div>
          <div style={{ marginTop: 28, fontSize: 32, color: "#0f62fe" }}>{SITE.name}</div>
        </div>
        <div style={{ height: 10, width: "100%", background: "linear-gradient(90deg, #6d28d9, #2563eb, #0891b2, #059669, #ca8a04, #ea580c, #dc2626)" }} />
      </div>
    ),
    size,
  );
}
