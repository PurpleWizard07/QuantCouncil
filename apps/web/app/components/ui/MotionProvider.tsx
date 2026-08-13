"use client";

import type { ReactNode } from "react";
import { MotionConfig } from "motion/react";

/**
 * Root-level motion config. reducedMotion="user" makes every Motion-driven
 * animation in the app defer to the OS-level prefers-reduced-motion setting
 * automatically -- individual components never need to check it themselves.
 */
export function MotionProvider({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
