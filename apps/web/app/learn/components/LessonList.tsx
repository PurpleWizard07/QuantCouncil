"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { isLessonComplete, PROGRESS_EVENT } from "@/app/learn/lib/progress";

export interface LessonListItem {
  slug: string;
  title: string;
  status: "ready" | "outline";
  critical?: boolean;
}

/** Clickable vertical lesson tracker for a module page -- numbered, ticks off as lessons are marked complete. */
export function LessonList({ moduleSlug, lessons }: { moduleSlug: string; lessons: LessonListItem[] }) {
  const [completed, setCompleted] = useState<Set<string>>(new Set());

  useEffect(() => {
    const recompute = () =>
      setCompleted(new Set(lessons.filter((l) => isLessonComplete(`${moduleSlug}/${l.slug}`)).map((l) => l.slug)));
    recompute();
    window.addEventListener(PROGRESS_EVENT, recompute);
    return () => window.removeEventListener(PROGRESS_EVENT, recompute);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moduleSlug, lessons.map((l) => l.slug).join(",")]);

  return (
    <ol className="flex flex-col gap-1">
      {lessons.map((lesson, i) => {
        const done = completed.has(lesson.slug);
        return (
          <li key={lesson.slug}>
            <Link
              href={`/learn/${moduleSlug}/${lesson.slug}`}
              className="group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-white/[0.04]"
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${
                  done ? "border-positive bg-positive text-bg" : "border-white/10 bg-white/[0.03] text-text-faint"
                }`}
              >
                {done ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                    <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  i + 1
                )}
              </span>
              <span className="flex-1 text-sm text-text group-hover:text-accent">{lesson.title}</span>
              {lesson.critical && (
                <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-warning">Must read</span>
              )}
              {lesson.status === "outline" && (
                <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-text-faint">Outline</span>
              )}
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="shrink-0 text-text-faint group-hover:text-accent">
                <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
