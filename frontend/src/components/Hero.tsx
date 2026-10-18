"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const BACKGROUND_VIDEO = "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260912_104303_0c6d60b2-9353-408e-9449-585108a22fb5.mp4";
const BACKGROUND_POSTER = "https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/130837c4-0244-4f37-9c61-8d801d93fd29.jpg";

export function Hero() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncPlayback = () => {
      if (reducedMotion.matches) {
        video.pause();
        return;
      }
      void video.play().catch(() => {});
    };

    syncPlayback();
    if (reducedMotion.addEventListener) {
      reducedMotion.addEventListener("change", syncPlayback);
      return () => reducedMotion.removeEventListener("change", syncPlayback);
    }

    reducedMotion.addListener(syncPlayback);
    return () => reducedMotion.removeListener(syncPlayback);
  }, []);

  return (
    <section
      id="home"
      className="relative isolate flex min-h-[100svh] flex-col justify-center overflow-hidden bg-[#03060c] bg-cover bg-center text-hero-ink"
    >
      <video
        ref={videoRef}
        className="absolute inset-0 -z-20 h-full w-full object-cover object-center contrast-[1.06] saturate-[1.15]"
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        poster={BACKGROUND_POSTER}
        src={BACKGROUND_VIDEO}
        aria-hidden="true"
      />
      {/* A centered veil keeps the headline readable over the bright focal point. */}
      <div
        className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_center,rgba(3,6,12,0.70)_0%,rgba(3,6,12,0.50)_42%,rgba(3,6,12,0.22)_100%)]"
        aria-hidden
      />
      <div className="absolute inset-x-0 bottom-0 -z-10 h-1/3 bg-linear-to-t from-hero/80 to-transparent" aria-hidden />

      <div className="mx-auto w-full max-w-7xl px-6 py-28 md:px-10">
        <div className="mx-auto max-w-4xl text-center">
          <p className="mx-auto inline-flex rounded-full border border-white/25 bg-black/20 px-4 py-2 text-xs font-medium tracking-[0.14em] text-white/90 shadow-lg backdrop-blur-md sm:text-sm">
            In-line spectroscopy · Art Fiber Systems
          </p>
          <h1 className="mx-auto mt-7 max-w-4xl text-balance text-[clamp(2.5rem,5.4vw,5.5rem)] font-semibold leading-[1.02] tracking-[-0.04em] text-white drop-shadow-[0_4px_24px_rgba(0,0,0,0.35)]">
            Turn a customer enquiry into a cited spectroscopy assessment
          </h1>
          <p className="mx-auto mt-7 max-w-3xl text-pretty text-base leading-relaxed text-white/85 drop-shadow-[0_2px_14px_rgba(0,0,0,0.35)] sm:text-lg md:text-xl">
            SpectraSense separates what the customer said from what is still unknown, recommends NIR, Raman, MIR or UV-Vis methods with page
            citations from the AFS material, and proposes a first feasibility experiment for an expert to review.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3 sm:gap-4">
            <Button
              asChild
              size="lg"
              className="group h-12 rounded-full border border-white/75 bg-white px-7 font-medium text-[#111827] shadow-[0_10px_32px_rgba(0,0,0,0.24)] transition duration-300 hover:-translate-y-0.5 hover:bg-white/90 hover:shadow-[0_16px_42px_rgba(0,0,0,0.32)]"
            >
              <Link href="/assess">Start an assessment <ArrowRight className="transition-transform group-hover:translate-x-0.5" aria-hidden /></Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline-inverse"
              className="h-12 rounded-full border-white/60 bg-white/10 px-7 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.18)] backdrop-blur-md transition duration-300 hover:-translate-y-0.5 hover:border-white/85 hover:bg-white/20 hover:shadow-[0_12px_28px_rgba(0,0,0,0.2)]"
            >
              <Link href="/how-it-works">See how it works</Link>
            </Button>
          </div>
        </div>
      </div>
      <div className="spectrum-line absolute inset-x-0 bottom-0 h-1.5" aria-hidden />
    </section>
  );
}
