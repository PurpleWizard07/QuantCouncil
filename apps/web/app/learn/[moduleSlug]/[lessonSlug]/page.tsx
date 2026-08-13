import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { LessonContent } from "@/app/learn/components/LessonContent";
import { MarginNote } from "@/app/learn/components/MarginNote";
import { MarginNoteProvider } from "@/app/learn/components/MarginNoteProvider";
import { MarkCompleteButton } from "@/app/learn/components/MarkCompleteButton";
import { TableOfContents } from "@/app/learn/components/TableOfContents";
import { readLessonSource } from "@/app/learn/lib/content";
import { adjacentLessons, allLessonRefs, CURRICULUM, getLesson, progressId } from "@/app/learn/lib/curriculum";
import { extractHeadings } from "@/app/learn/lib/headings";
import { estimateReadingMinutes } from "@/app/learn/lib/readingTime";

interface Params {
  moduleSlug: string;
  lessonSlug: string;
}

export function generateStaticParams() {
  return allLessonRefs().map((r) => ({ moduleSlug: r.moduleSlug, lessonSlug: r.lessonSlug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { moduleSlug, lessonSlug } = await params;
  const found = getLesson(moduleSlug, lessonSlug);
  return { title: found ? `${found.lesson.title} — Learn — QuantCouncil` : "Learn — QuantCouncil" };
}

function refTitle(ref: { moduleSlug: string; lessonSlug: string } | null) {
  if (!ref) return null;
  const module = CURRICULUM.find((m) => m.slug === ref.moduleSlug);
  const lesson = module?.lessons.find((l) => l.slug === ref.lessonSlug);
  return lesson ? { title: lesson.title, module } : null;
}

export default async function LessonPage({ params }: { params: Promise<Params> }) {
  const { moduleSlug, lessonSlug } = await params;
  const found = getLesson(moduleSlug, lessonSlug);
  if (!found) notFound();
  const { module, lesson } = found;

  const source = readLessonSource(module.slug, lesson.slug);
  if (!source) notFound();

  const headings = extractHeadings(source);
  const minutes = estimateReadingMinutes(source);
  const { prev, next } = adjacentLessons(module.slug, lesson.slug);
  const prevInfo = refTitle(prev);
  const nextInfo = refTitle(next);

  return (
    <MarginNoteProvider>
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_240px]">
        <article className="min-w-0">
          <nav className="mb-4 flex items-center gap-1.5 text-xs text-text-faint">
            <Link href="/learn" className="hover:text-accent">
              Learn
            </Link>
            <span>/</span>
            <Link href={`/learn/${module.slug}`} className="hover:text-accent">
              {module.title}
            </Link>
          </nav>

          <div className="mb-5 flex flex-wrap items-center gap-2 text-[11px] font-medium uppercase tracking-wide text-text-faint">
            <span>{minutes} min read</span>
            {lesson.status === "outline" && <span className="text-text-faint">· Being expanded</span>}
            {lesson.critical && <span className="text-warning">· Must read</span>}
          </div>

          {lesson.constitutionFlag && (
            <div className="mb-6 flex items-start gap-2.5 rounded-xl border border-negative/30 bg-negative-soft px-4 py-3 text-sm text-negative">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="mt-0.5 shrink-0">
                <path d="M12 3l9 16H3L12 3z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
                <path d="M12 10v4M12 16.8v.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
              <span>
                <strong>Educational only.</strong> QuantCouncil&rsquo;s paper-trading engine (v1) is long-only cash
                equities — this isn&rsquo;t simulated in the product yet.
              </span>
            </div>
          )}

          <div className="prose-learn">
            <LessonContent source={source} />
          </div>

          <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-6">
            <MarkCompleteButton lessonId={progressId(module.slug, lesson.slug)} />
          </div>

          <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {prev && prevInfo ? (
              <Link
                href={`/learn/${prev.moduleSlug}/${prev.lessonSlug}`}
                className="surface rounded-xl p-4 hover:border-white/20"
              >
                <div className="text-[11px] uppercase tracking-wide text-text-faint">← Previous</div>
                <div className="mt-1 text-sm text-text">{prevInfo.title}</div>
              </Link>
            ) : (
              <span />
            )}
            {next && nextInfo && (
              <Link
                href={`/learn/${next.moduleSlug}/${next.lessonSlug}`}
                className="surface rounded-xl p-4 text-right hover:border-white/20"
              >
                <div className="text-[11px] uppercase tracking-wide text-text-faint">Next →</div>
                <div className="mt-1 text-sm text-text">{nextInfo.title}</div>
              </Link>
            )}
          </div>
        </article>

        <aside className="hidden lg:block">
          <div className="sticky top-24 flex flex-col gap-4">
            <MarginNote />
            <TableOfContents headings={headings} />
          </div>
        </aside>
      </div>
    </MarginNoteProvider>
  );
}
