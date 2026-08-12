import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { GlassCard } from "@/app/components/ui/GlassCard";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { LessonList } from "@/app/learn/components/LessonList";
import { ModuleProgressBar } from "@/app/learn/components/ModuleProgressBar";
import { CURRICULUM, getModule, progressId } from "@/app/learn/lib/curriculum";

export function generateStaticParams() {
  return CURRICULUM.map((m) => ({ moduleSlug: m.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ moduleSlug: string }> }): Promise<Metadata> {
  const { moduleSlug } = await params;
  const module = getModule(moduleSlug);
  return { title: module ? `${module.title} — Learn — QuantCouncil` : "Learn — QuantCouncil" };
}

export default async function ModulePage({ params }: { params: Promise<{ moduleSlug: string }> }) {
  const { moduleSlug } = await params;
  const module = getModule(moduleSlug);
  if (!module) notFound();

  const lessonIds = module.lessons.map((l) => progressId(module.slug, l.slug));

  return (
    <MotionPage>
      <nav className="mb-4 text-xs text-text-faint">
        <Link href="/learn" className="hover:text-accent">
          Learn
        </Link>
        <span className="px-1.5">/</span>
        <span className="text-text-muted">{module.title}</span>
      </nav>

      <PageHeader title={module.title} subtitle={module.description} />

      {module.constitutionFlag && (
        <div className="mb-6 flex items-start gap-2.5 rounded-xl border border-negative/30 bg-negative-soft px-4 py-3 text-sm text-negative">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="mt-0.5 shrink-0">
            <path d="M12 3l9 16H3L12 3z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
            <path d="M12 10v4M12 16.8v.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <span>
            <strong>Educational only.</strong> QuantCouncil&rsquo;s paper-trading engine (v1) is long-only cash
            equities — nothing in this module is simulated in the product yet.
          </span>
        </div>
      )}

      <GlassCard className="mb-6">
        <ModuleProgressBar lessonIds={lessonIds} label="Module progress" />
      </GlassCard>

      <GlassCard padding="sm">
        <LessonList
          moduleSlug={module.slug}
          lessons={module.lessons.map((l) => ({ slug: l.slug, title: l.title, status: l.status, critical: l.critical }))}
        />
      </GlassCard>
    </MotionPage>
  );
}
