// Site identity used by metadata, the sitemap, structured data and the social image.
// Set NEXT_PUBLIC_SITE_URL to the deployed address so canonical and Open Graph URLs are absolute.
export const SITE = {
  name: "SpectraSense",
  url: (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000").replace(/\/$/, ""),
  title: "SpectraSense — cited first assessments for in-line spectroscopy",
  description:
    "Turn a customer enquiry into a first in-line spectroscopy assessment: stated facts and unknowns, NIR, Raman, MIR or UV-Vis methods with page citations, premise checks and a feasibility plan.",
  keywords: ["in-line spectroscopy", "process analytical technology", "NIR spectroscopy", "Raman spectroscopy", "MIR ATR", "UV-Vis",
    "fiber optic probe", "feasibility study", "Art Fiber Systems"],
};
