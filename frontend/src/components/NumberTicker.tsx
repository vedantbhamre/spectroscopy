"use client";

import { useEffect, useRef, useState } from "react";
import { useInView, useReducedMotion } from "motion/react";
import { AnimatedNumber } from "./motion-primitives/animated-number";

// Counts up to a value when it scrolls into view, with motion-primitives' AnimatedNumber (a spring).
// The server renders the final value as text, so search engines, no-JS and reduced-motion users see the real number.
export function NumberTicker({ value, decimals = 0, suffix = "", className = "" }: { value: number; decimals?: number; suffix?: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "0px 0px -10% 0px" });
  const reduce = useReducedMotion();
  const [target, setTarget] = useState<number | null>(null); // null = static final text

  useEffect(() => {
    if (!inView || reduce || target !== null) return;
    setTarget(0);
    const id = requestAnimationFrame(() => setTarget(value));
    return () => cancelAnimationFrame(id);
  }, [inView, reduce, target, value]);

  return (
    <span ref={ref} className={`tabular-nums ${className}`}>
      <span className="sr-only">{`${value.toFixed(decimals)}${suffix}`}</span>
      <span aria-hidden>
        {target === null ? value.toFixed(decimals) : <AnimatedNumber value={target} decimals={decimals} springOptions={{ bounce: 0, visualDuration: 1.1 }} />}
        {suffix}
      </span>
    </span>
  );
}
