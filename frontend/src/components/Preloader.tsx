"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export function Preloader() {
  const [loading, setLoading] = useState(true);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const durationMs = 1400;
    let raf = 0;
    let done: ReturnType<typeof setTimeout>;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / durationMs);
      setCount(Math.round(p * 100));
      if (p < 1) raf = requestAnimationFrame(tick);
      else done = setTimeout(() => setLoading(false), 250);
    };
    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); clearTimeout(done); };
  }, []);

  return (
    <AnimatePresence>
      {loading && (
        <motion.div
          key="preloader"
          initial={{ y: 0 }}
          exit={{ y: "-100%" }}
          transition={{ duration: 0.9, ease: [0.76, 0, 0.24, 1] }}
          className="pointer-events-none fixed inset-0 z-[100] flex h-screen w-full flex-col items-center justify-center bg-night"
        >
          <motion.div exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.3 }} className="text-2xl font-semibold tracking-tight text-night-ink sm:text-3xl">
            SpectraSense AI
          </motion.div>
          <motion.div exit={{ opacity: 0 }} className="spectrum-line mt-4 h-0.5 rounded" style={{ width: `${count * 1.6}px` }} />
          <motion.div exit={{ opacity: 0 }} className="mt-3 font-mono text-sm tabular-nums text-amber">{count}%</motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
