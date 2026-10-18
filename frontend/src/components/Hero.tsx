"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef } from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

// Intro frames (1280×720) played as the full-screen hero background. Only frames without text are used —
// the probe in the line (1–7), the light split into its spectrum (20–30) and the spectrum trace (31–39) — so
// nothing in the footage competes with the headline. (The dashboard and title-card frames are not shipped.)
// Smooth playback: redraw at the display refresh rate, cross-fade continuously between neighbouring frames by
// elapsed time, and dissolve slowly across each scene change and the loop wrap.
const SEQUENCE = [...range(1, 7), ...range(20, 39)];
const FPS = 9; // source frames per second; one loop ≈ 3 s
const SCENE_DISSOLVE = 3; // frames over which one scene dissolves into the next

function range(a: number, b: number) {
  return Array.from({ length: b - a + 1 }, (_, k) => a + k);
}
// Index of the last frame of each scene (where the next frame is not the next source frame).
const SCENE_ENDS = SEQUENCE.map((f, k) => (SEQUENCE[(k + 1) % SEQUENCE.length] !== f + 1 ? k : -1)).filter((k) => k >= 0);
const TOTAL = SEQUENCE.length;

const framePath = (frame: number) => `/frames/ezgif-frame-${String(frame).padStart(3, "0")}.jpg`;

export function Hero() {
  const sectionRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imagesRef = useRef<HTMLImageElement[]>([]);
  const positionRef = useRef(0); // playback position in frames (fractional)

  // Draw a frame scaled to cover the canvas (cropped, never letterboxed).
  const drawCover = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, i: number, alpha: number) => {
    const img = imagesRef.current[i];
    if (!img?.complete || img.naturalWidth === 0 || alpha <= 0) return;
    const scale = Math.max(canvas.width / img.naturalWidth, canvas.height / img.naturalHeight);
    const w = img.naturalWidth * scale;
    const h = img.naturalHeight * scale;
    ctx.globalAlpha = Math.min(alpha, 1);
    ctx.drawImage(img, (canvas.width - w) / 2, (canvas.height - h) / 2, w, h);
    ctx.globalAlpha = 1;
  }, []);

  const draw = useCallback((position: number) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const i = Math.floor(position) % TOTAL;
    const frac = position - Math.floor(position);
    const end = SCENE_ENDS.find((e) => i <= e && i > e - SCENE_DISSOLVE);
    if (end === undefined) {
      drawCover(ctx, canvas, i, 1);
      drawCover(ctx, canvas, (i + 1) % TOTAL, frac); // continuous blend into the next frame
    } else {
      // Across a scene change: hold this scene's frames and fade the next scene's first frame in slowly.
      drawCover(ctx, canvas, i, 1);
      drawCover(ctx, canvas, Math.min(i + 1, end), frac);
      drawCover(ctx, canvas, (end + 1) % TOTAL, (i - (end - SCENE_DISSOLVE + 1) + frac) / SCENE_DISSOLVE);
    }
  }, [drawCover]);

  const resize = useCallback(() => {
    const canvas = canvasRef.current;
    const box = sectionRef.current;
    if (!canvas || !box) return;
    const { width, height } = box.getBoundingClientRect();
    if (!width || !height) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext("2d");
    if (ctx) { ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high"; }
    draw(positionRef.current);
  }, [draw]);

  useEffect(() => {
    let cancelled = false;
    let rafId = 0;
    let visible = true;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const play = () => {
      if (cancelled || reduce) return;
      let last = performance.now();
      const tick = (now: number) => {
        if (cancelled) return;
        if (visible && !document.hidden) {
          // Advance by elapsed time; clamp long gaps (tab switches) so playback never jumps.
          positionRef.current = (positionRef.current + (Math.min(now - last, 100) / 1000) * FPS) % TOTAL;
          draw(positionRef.current);
        }
        last = now;
        rafId = requestAnimationFrame(tick);
      };
      rafId = requestAnimationFrame(tick);
    };

    // Decode every frame before playing, so the first loop does not stutter while images decode.
    imagesRef.current = SEQUENCE.map((frame) => {
      const img = new Image();
      img.decoding = "async";
      img.src = framePath(frame);
      return img;
    });
    imagesRef.current[0].decode().then(resize, resize);
    Promise.allSettled(imagesRef.current.map((img) => img.decode())).then(() => { if (!cancelled) play(); });

    const ro = new ResizeObserver(resize);
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    if (sectionRef.current) { ro.observe(sectionRef.current); io.observe(sectionRef.current); }

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafId);
      ro.disconnect();
      io.disconnect();
    };
  }, [draw, resize]);

  return (
    <section
      ref={sectionRef}
      id="home"
      className="relative isolate flex min-h-[calc(100svh-3.5rem)] flex-col justify-end overflow-hidden bg-hero bg-cover bg-center text-hero-ink"
      style={{ backgroundImage: `url(${framePath(SEQUENCE[0])})` }}
    >
      <canvas
        ref={canvasRef}
        className="absolute inset-0 -z-20 h-full w-full contrast-[1.06] saturate-[1.15]"
        aria-label="Animation: an AFS fibre-optic probe in a process line, its light split into the spectrum"
        role="img"
      />
      {/* Scrims keep the text readable over any frame: from the left on wide screens, from the bottom everywhere. */}
      <div
        className="absolute inset-0 -z-10 bg-hero/55 md:bg-transparent md:bg-[linear-gradient(90deg,var(--hero)_0%,color-mix(in_srgb,var(--hero)_82%,transparent)_30%,color-mix(in_srgb,var(--hero)_35%,transparent)_48%,transparent_62%)]"
        aria-hidden
      />
      <div className="absolute inset-x-0 bottom-0 -z-10 h-1/2 bg-linear-to-t from-hero via-hero/40 to-transparent" aria-hidden />

      <div className="mx-auto w-full max-w-7xl px-6 pb-20 pt-28 md:px-10 md:pb-28">
        <div className="max-w-xl lg:max-w-[38rem]">
          <p className="text-sm text-hero-ink-2">In-line spectroscopy · Art Fiber Systems</p>
          <h1 className="mt-4 text-[clamp(2.5rem,4.6vw,4rem)] font-light leading-[1.06] tracking-[-0.015em]">
            Turn a customer enquiry into a cited spectroscopy assessment
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-hero-ink-2">
            SpectraSense separates what the customer said from what is still unknown, recommends NIR, Raman, MIR or UV-Vis methods with page
            citations from the AFS material, and proposes a first feasibility experiment for an expert to review.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/assess">Start an assessment <ArrowRight aria-hidden /></Link>
            </Button>
            <Button asChild size="lg" variant="outline-inverse">
              <Link href="/how-it-works">See how it works</Link>
            </Button>
          </div>
        </div>
      </div>
      <div className="spectrum-line absolute inset-x-0 bottom-0 h-1.5" aria-hidden />
    </section>
  );
}
