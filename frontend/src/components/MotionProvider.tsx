"use client";

import { MotionConfig } from "motion/react";

// Every motion animation follows the user's reduced-motion setting (transforms and layout animations stop).
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
