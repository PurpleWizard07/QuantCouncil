import type { Transition } from "motion/react";

/**
 * Shared motion vocabulary for the app. Every transition should come from
 * here rather than a hand-rolled { duration, ease } object, so timing reads
 * as one coherent physical system instead of a grab-bag of one-off values.
 * Reduced-motion is handled globally (MotionProvider + globals.css) --
 * nothing here needs its own check.
 */

/** Duration ladder, in seconds. Nothing should sit off this ladder. */
export const DURATION = {
  /** Hover/press feedback, toggles. */
  state: 0.12,
  /** A single element entering/leaving/moving. */
  element: 0.24,
  /** A panel, drawer, or card-sized surface changing. */
  surface: 0.42,
  /** A multi-element orchestrated moment (the veto seal, verdict convergence). */
  ceremony: 0.7,
} as const;

/** Single damped-deceleration curve used for every eased (non-spring) transition. */
export const EASE = [0.22, 1, 0.36, 1] as const;

/** Spring preset for things that should feel nudged, not eased: drawers, magnetic buttons, layoutId transforms. */
export const SPRING: Transition = {
  type: "spring",
  stiffness: 380,
  damping: 32,
  mass: 0.9,
};

export const TRANSITION: Record<keyof typeof DURATION | "spring", Transition> = {
  state: { duration: DURATION.state, ease: EASE },
  element: { duration: DURATION.element, ease: EASE },
  surface: { duration: DURATION.surface, ease: EASE },
  ceremony: { duration: DURATION.ceremony, ease: EASE },
  spring: SPRING,
};

/** Delay between siblings in a staggered list entrance -- pair with TRANSITION.element. */
export const STAGGER_STEP = 0.04;
