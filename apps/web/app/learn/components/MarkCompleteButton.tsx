"use client";

import { useEffect, useState } from "react";

import { Button } from "@/app/components/ui/Button";
import { useToast } from "@/app/components/ui/Toast";
import { isLessonComplete, setLessonComplete } from "@/app/learn/lib/progress";

export function MarkCompleteButton({ lessonId }: { lessonId: string }) {
  const [complete, setComplete] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { showToast } = useToast();

  useEffect(() => {
    setComplete(isLessonComplete(lessonId));
    setMounted(true);
  }, [lessonId]);

  const toggle = () => {
    const next = !complete;
    setComplete(next);
    setLessonComplete(lessonId, next);
    showToast(next ? "Lesson marked complete" : "Marked incomplete", next ? "success" : "info");
  };

  if (!mounted) return <div className="h-9 w-40" aria-hidden="true" />;

  return (
    <Button
      variant={complete ? "secondary" : "primary"}
      onClick={toggle}
      icon={
        complete ? (
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : undefined
      }
    >
      {complete ? "Completed" : "Mark as complete"}
    </Button>
  );
}
