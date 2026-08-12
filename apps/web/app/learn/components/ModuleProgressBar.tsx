"use client";

import { useEffect, useState } from "react";

import { MetricBar } from "@/app/components/ui/charts/MetricBar";
import { completedCount, PROGRESS_EVENT } from "@/app/learn/lib/progress";

export function ModuleProgressBar({ lessonIds, label = "Progress" }: { lessonIds: string[]; label?: string }) {
  const [done, setDone] = useState(0);

  useEffect(() => {
    const recompute = () => setDone(completedCount(lessonIds));
    recompute();
    window.addEventListener(PROGRESS_EVENT, recompute);
    return () => window.removeEventListener(PROGRESS_EVENT, recompute);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonIds.join(",")]);

  if (lessonIds.length === 0) return null;

  return (
    <MetricBar
      label={label}
      value={done / lessonIds.length}
      valueLabel={`${done}/${lessonIds.length}`}
      variant={done === lessonIds.length ? "positive" : "accent"}
    />
  );
}
