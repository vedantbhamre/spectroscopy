"use client";

import { useEffect, useRef, useState } from "react";
import type { AnimationItem } from "lottie-web";
import { arrive, hexToRgb, OUT, pipelineAnimation } from "@/lib/lottie-pipeline";

const STEPS = [
  { title: "Read the enquiry", text: "What the client said is kept apart from everything they did not say." },
  { title: "Facts and unknowns", text: "Stated facts keep their wording; missing facts stay unknown, never guessed." },
  { title: "Retrieve AFS pages", text: "The relevant pages of the AFS guides, slides and studies are found, with the method comparison table." },
  { title: "Premise checks", text: "Does the fibre transmit the method's range? Is a lab study being used as proof?" },
  { title: "Cited report", text: "Questions, methods, concept and a first experiment, each claim with its page." },
];

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name);

export function PipelineLottie() {
  const box = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState(-1);

  useEffect(() => {
    let item: AnimationItem | undefined;
    let cancelled = false;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const mount = async () => {
      const lottie = (await import("lottie-web")).default;
      if (cancelled || !box.current) return;
      item?.destroy();
      item = lottie.loadAnimation({
        container: box.current,
        renderer: "svg",
        loop: true,
        autoplay: !reduce,
        animationData: pipelineAnimation({ ink: hexToRgb(css("--ink")), paper: hexToRgb(css("--bg")), accent: hexToRgb(css("--violet")) }),
        rendererSettings: { preserveAspectRatio: "xMidYMid meet" },
      });
      if (reduce) { item.goToAndStop(OUT - 50, true); setStep(4); return; }
      let last = -1;
      item.addEventListener("enterFrame", (e: unknown) => {
        const t = (e as { currentTime: number }).currentTime;
        let s = -1;
        for (let i = 0; i < 5; i++) if (t >= arrive(i)) s = i;
        if (t > 380) s = -1;
        if (s !== last) { last = s; setStep(s); }
      });
    };
    mount();

    // Rebuild with the new colours when the theme toggles.
    const mo = new MutationObserver(() => mount());
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    // Pause while off screen.
    const io = new IntersectionObserver(([e]) => {
      if (reduce) return;
      if (e.isIntersecting) item?.play();
      else item?.pause();
    });
    if (box.current) io.observe(box.current);

    return () => { cancelled = true; mo.disconnect(); io.disconnect(); item?.destroy(); };
  }, []);

  return (
    <figure>
      <div ref={box} className="aspect-[1200/260] w-full" role="img" aria-label="Animation of the assessment pipeline: enquiry, facts and unknowns, AFS pages, premise checks, cited report" />
      <figcaption className="mt-2 grid gap-6 sm:grid-cols-5 sm:gap-4">
        {STEPS.map((s, i) => (
          <div key={s.title} className={`transition-opacity duration-500 sm:text-center ${step >= i ? "opacity-100" : "opacity-45"}`}>
            <div className="font-mono text-[11px] tracking-[0.08em] text-ink-3">0{i + 1}</div>
            <div className={`mt-1 text-[17px] tracking-[-0.02em] transition-colors duration-500 ${step === i ? "text-violet" : "text-ink"}`} style={{ fontWeight: 450 }}>{s.title}</div>
            <p className="mx-auto mt-1.5 max-w-[22ch] text-sm leading-relaxed text-ink-2">{s.text}</p>
          </div>
        ))}
      </figcaption>
    </figure>
  );
}
