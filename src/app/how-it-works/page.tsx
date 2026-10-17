import { SiteHeader } from "@/components/SiteHeader";
import { Workbench } from "@/components/Workbench";

export const metadata = { title: "How it works · SpectraSense AI" };

export default function HowItWorksPage() {
  return (
    <>
      <SiteHeader />
      <Workbench mode="examples" />
    </>
  );
}
