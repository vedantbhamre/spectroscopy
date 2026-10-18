import type { MetadataRoute } from "next";
import { SITE } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = [
    { path: "", priority: 1 },
    { path: "/assess", priority: 0.9 },
    { path: "/how-it-works", priority: 0.8 },
    { path: "/evals", priority: 0.6 },
  ];
  return pages.map((p) => ({ url: `${SITE.url}${p.path}`, lastModified: new Date(), changeFrequency: "weekly", priority: p.priority }));
}
