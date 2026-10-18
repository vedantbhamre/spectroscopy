import type { Metadata } from "next";
import { SiteHeader } from "@/components/SiteHeader";
import { Workbench } from "@/components/Workbench";

export const metadata: Metadata = {
  title: "Start an assessment",
  description: "Describe a customer's process and what they need to measure. SpectraSense drafts a cited first assessment: facts, unknowns, questions, methods, spectral range, risks and a first experiment.",
  alternates: { canonical: "/assess" },
};

export default function AssessPage() {
  return (
    <>
      <SiteHeader />
      <main>
        <h1 className="sr-only">Start an in-line spectroscopy assessment</h1>
        <Workbench />
      </main>
    </>
  );
}
