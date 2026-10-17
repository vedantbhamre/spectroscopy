"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef } from "react";
import { ArrowDown, ArrowRight, BookOpen } from "lucide-react";
import { Reveal } from "./Reveal";

// Frames from the SpectraSense intro (1280×720), auto-played on a canvas in a loop —
// same approach as the React portfolio hero, independent of scrolling.
const TOTAL_FRAMES = 52;
const FPS = 12;
// Last frames dissolve into frame 0 so the loop wraps without a hard cut.
const CROSSFADE_FRAMES = 6;
// Never upscale the sharp foreground past this multiple of native resolution.
const MAX_UPSCALE = 1.4;
// The blurred backdrop is indistinct by design; update it only every few frames.
const BG_UPDATE_EVERY = 3;

const framePath = (i: number) => `/frames/ezgif-frame-${String(i + 1).padStart(3, "0")}.jpg`;

export function Hero() {
  const boxRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const imagesRef = useRef<HTMLImageElement[]>([]);
  const currentRef = useRef(0);
  const bgTickRef = useRef(0);

  const drawSingle = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, i: number, alpha: number) => {
    const img = imagesRef.current[i];
    if (!img?.complete || img.naturalWidth === 0) return;
    const imgRatio = img.naturalWidth / img.naturalHeight;
    let w: number, h: number;
    if (canvas.width / canvas.height > imgRatio) { h = canvas.height; w = h * imgRatio; }
    else { w = canvas.width; h = w / imgRatio; }
    if (w / img.naturalWidth > MAX_UPSCALE) { w = img.naturalWidth * MAX_UPSCALE; h = img.naturalHeight * MAX_UPSCALE; }
    ctx.globalAlpha = alpha;
    ctx.drawImage(img, (canvas.width - w) / 2, (canvas.height - h) / 2, w, h);
    ctx.globalAlpha = 1;
  }, []);

  const drawFrame = useCallback((i: number) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawSingle(ctx, canvas, i, 1);
    const windowStart = TOTAL_FRAMES - CROSSFADE_FRAMES;
    if (i >= windowStart) drawSingle(ctx, canvas, 0, (i - windowStart + 1) / CROSSFADE_FRAMES);
    bgTickRef.current += 1;
    if (bgRef.current && bgTickRef.current % BG_UPDATE_EVERY === 0) bgRef.current.style.backgroundImage = `url(${framePath(i)})`;
  }, [drawSingle]);

  const handleResize = useCallback(() => {
    const canvas = canvasRef.current;
    const box = boxRef.current;
    if (!canvas || !box) return;
    const { width, height } = box.getBoundingClientRect();
    if (!width || !height) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    if (ctx) { ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high"; }
    drawFrame(currentRef.current);
  }, [drawFrame]);

  useEffect(() => {
    let cancelled = false;
    let rafId = 0;
    let visible = true;
    let loaded = 0;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const start = () => {
      if (cancelled || reduce) return;
      let last = performance.now();
      const interval = 1000 / FPS;
      const animate = (now: number) => {
        if (cancelled) return;
        if (visible && !document.hidden && now - last >= interval) {
          currentRef.current = (currentRef.current + 1) % TOTAL_FRAMES;
          drawFrame(currentRef.current);
          last = now;
        }
        rafId = requestAnimationFrame(animate);
      };
      rafId = requestAnimationFrame(animate);
    };

    imagesRef.current = Array.from({ length: TOTAL_FRAMES }, (_, i) => {
      const img = new Image();
      const done = () => {
        if (cancelled) return;
        loaded += 1;
        if (i === 0) {
          handleResize();
          if (bgRef.current) bgRef.current.style.backgroundImage = `url(${framePath(0)})`;
        }
        if (loaded === TOTAL_FRAMES) start();
      };
      img.onload = done;
      img.onerror = done;
      img.src = framePath(i);
      return img;
    });

    const ro = new ResizeObserver(handleResize);
    // Pause playback while the hero is off screen.
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; });
    if (boxRef.current) { ro.observe(boxRef.current); io.observe(boxRef.current); }

    return () => {
      cancelled = true;
      cancelAnimationFrame(rafId);
      ro.disconnect();
      io.disconnect();
    };
  }, [drawFrame, handleResize]);

  return (
    <section id="home" className="relative flex min-h-screen w-full items-center overflow-hidden bg-night pb-16 pt-28 md:pb-0 md:pt-24">
      <div className="relative z-20 mx-auto grid w-full max-w-7xl items-center gap-12 px-6 md:grid-cols-[5fr_7fr] md:gap-10 md:px-10 lg:gap-14">
        {/* Text column — its own space, never on top of the footage */}
        <div className="order-2 flex flex-col items-start text-left md:order-1">
          <Reveal>
            <div className="mb-6 inline-flex items-center gap-2 rounded-md border border-night-line bg-night-2/60 px-3.5 py-1.5 text-xs font-medium text-night-ink-2 backdrop-blur-md">
              <span className="h-1.5 w-1.5 rounded-md bg-accent-bright" />
              Art Fiber Systems · AI assessment assistant
            </div>
          </Reveal>
          <Reveal delay={0.08}>
            <p className="mb-3 text-sm font-medium text-accent-bright">From process challenges to in-line measurement solutions</p>
          </Reveal>
          <Reveal delay={0.14}>
            <h1 className="mb-6 text-4xl font-semibold leading-[1.05] tracking-tight text-night-ink sm:text-5xl lg:text-6xl">SpectraSense AI</h1>
          </Reveal>
          <Reveal delay={0.22}>
            <p className="mb-9 max-w-xl text-base leading-relaxed text-night-ink-2 md:text-lg">
              Customers know what they need to monitor, not which method, spectral range, fiber probe or setup to test first. SpectraSense turns a short enquiry into a first technical assessment an AFS expert can review in minutes.
            </p>
          </Reveal>
          <Reveal delay={0.3}>
            <div className="flex flex-row flex-wrap items-center gap-3">
              <Link href="/assess" className="inline-flex items-center gap-2 rounded-md bg-accent px-6 py-3 text-sm font-semibold text-white transition-all duration-300 hover:bg-accent-dim">
                Start an assessment <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/reference" className="inline-flex items-center gap-2 rounded-md border border-night-line px-6 py-3 text-sm font-semibold text-night-ink backdrop-blur-md transition-all duration-300 hover:bg-night-3">
                <BookOpen className="h-4 w-4" /> Methods &amp; fibers
              </Link>            </div>
          </Reveal>
        </div>

        {/* Frame box — a rounded card on the light hero */}
        <Reveal variant="left" delay={0.1} className="order-1 w-full md:order-2">
          <div
            ref={boxRef}
            className="relative aspect-video w-full overflow-hidden rounded-2xl bg-[#0b1020] shadow-2xl shadow-slate-900/20 ring-1 ring-line"
          >
            <div ref={bgRef} className="absolute -inset-8 z-0 scale-110 bg-cover bg-center blur-3xl brightness-[0.45] saturate-[1.15]" />
            <canvas ref={canvasRef} className="hero-zoom absolute left-0 top-0 z-[1] h-full w-full contrast-[1.08] saturate-[1.12]" aria-label="SpectraSense intro animation" role="img" />
          </div>
        </Reveal>
      </div>

      <div className="pointer-events-none absolute bottom-8 left-1/2 z-20 hidden -translate-x-1/2 flex-col items-center gap-2 text-night-ink-3 md:flex">
        <span className="text-[11px]">Scroll</span>
        <ArrowDown className="h-4 w-4 animate-bounce" />
      </div>
    </section>
  );
}
