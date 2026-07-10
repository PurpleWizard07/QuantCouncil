"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";

export interface MotionPageProps {
  children: ReactNode;
  className?: string;
}

/** Wrap a page's content in this for a consistent fade/slide-in entrance. */
export function MotionPage({ children, className = "" }: MotionPageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
