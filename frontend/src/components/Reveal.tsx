"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { motion, useAnimation, useInView, useReducedMotion, type HTMLMotionProps } from "motion/react";

const variants = {
  up: { hidden: { opacity: 0, y: 28 }, visible: { opacity: 1, y: 0 } },
  down: { hidden: { opacity: 0, y: -28 }, visible: { opacity: 1, y: 0 } },
  left: { hidden: { opacity: 0, x: 28 }, visible: { opacity: 1, x: 0 } },
  right: { hidden: { opacity: 0, x: -28 }, visible: { opacity: 1, x: 0 } },
  scale: { hidden: { opacity: 0, scale: 0.92 }, visible: { opacity: 1, scale: 1 } },
  fade: { hidden: { opacity: 0 }, visible: { opacity: 1 } },
};

type Props = HTMLMotionProps<"div"> & {
  variant?: keyof typeof variants;
  delay?: number;
  duration?: number;
  once?: boolean;
  amount?: number;
};

// Server HTML is always visible (search engines, no-JS, slow scripts). After mount, only content that is
// below the fold is hidden and revealed on scroll; content already on screen never animates in.
const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

export function Reveal({ children, variant = "up", delay = 0, duration = 0.7, once = true, amount = 0.2, ...props }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const controls = useAnimation();
  const reduce = useReducedMotion();
  const inView = useInView(ref, { once, amount });
  const [armed, setArmed] = useState(false);

  useIsoLayoutEffect(() => {
    const top = ref.current?.getBoundingClientRect().top ?? 0;
    if (!reduce && top > window.innerHeight) {
      controls.set("hidden");
      setArmed(true);
    }
  }, [controls, reduce]);

  useEffect(() => {
    if (armed && inView) controls.start("visible");
  }, [armed, inView, controls]);

  return (
    <motion.div ref={ref} initial={false} animate={controls} variants={variants[variant]} transition={{ duration, delay, ease: [0.22, 1, 0.36, 1] }} {...props}>
      {children}
    </motion.div>
  );
}
