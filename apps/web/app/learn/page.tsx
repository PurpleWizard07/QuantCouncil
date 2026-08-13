import Link from "next/link";
import type { Metadata } from "next";

import { GlassCard } from "@/app/components/ui/GlassCard";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { ModuleProgressBar } from "@/app/learn/components/ModuleProgressBar";
import { CURRICULUM, progressId } from "@/app/learn/lib/curriculum";

export const metadata: Metadata = {
  title: "Learn — QuantCouncil",
  description:
    "Trading Mastery: a first-principles knowledge base from market literacy through quantitative research, with Indian-market examples throughout.",
};

export default function LearnLandingPage() {
  return (
    <MotionPage>
      <PageHeader
        title="Learn"
        subtitle="Trading Mastery — a first-principles path from market literacy to quantitative research, with concrete Indian-market examples throughout. Educational content, not investment advice."
      />

      <Section
        title="Curriculum"
        description={`${CURRICULUM.length} modules, roughly in the order the source material recommends.`}
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {CURRICULUM.map((module, index) => {
            const lessonIds = module.lessons.map((l) => progressId(module.slug, l.slug));
            const outlineCount = module.lessons.filter((l) => l.status === "outline").length;
            return (
              <Link key={module.slug} href={`/learn/${module.slug}`} className="block">
                <GlassCard
                  variant={module.critical ? "warning" : "default"}
                  hover
                  className="flex h-full flex-col gap-3"
                >
                  <div className="flex items-start gap-3">
                    <span className="font-serif text-2xl leading-none text-warm/70">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="flex flex-1 items-start justify-between gap-2">
                      <h3 className="text-sm font-semibold text-text">{module.title}</h3>
                      {module.critical && (
                        <span className="shrink-0 rounded-full bg-warning-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-warning">
                          Must read
                        </span>
                      )}
                    </div>
                  </div>
                  {module.levelLabel && (
                    <span className="text-[11px] font-medium uppercase tracking-wide text-text-faint">
                      {module.levelLabel}
                    </span>
                  )}
                  <p className="flex-1 text-xs leading-relaxed text-text-muted">{module.description}</p>
                  <div className="flex items-center justify-between text-[11px] text-text-faint">
                    <span>{module.lessons.length} lessons</span>
                    {module.constitutionFlag && <span className="text-negative">Educational only</span>}
                    {!module.constitutionFlag && outlineCount > 0 && <span>{outlineCount} being expanded</span>}
                  </div>
                  <ModuleProgressBar lessonIds={lessonIds} />
                </GlassCard>
              </Link>
            );
          })}
        </div>
      </Section>

      <Section title="Reference" description="Cross-cutting lookups, not lessons in the sequence above.">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Link href="/learn/glossary" className="block">
            <GlassCard hover className="flex items-center gap-3">
              <span className="text-accent">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v18H6.5A1.5 1.5 0 0 1 5 19.5v-15z" stroke="currentColor" strokeWidth="1.6" />
                  <path d="M9 7.5h6M9 11h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              </span>
              <div>
                <div className="text-sm font-medium text-text">Glossary</div>
                <div className="text-xs text-text-muted">Every term: simple → technical → example.</div>
              </div>
            </GlassCard>
          </Link>
          <Link href="/learn/resources" className="block">
            <GlassCard hover className="flex items-center gap-3">
              <span className="text-accent">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M4 19.5V6.5A2 2 0 0 1 6 4.5h4l2 2h8a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" stroke="currentColor" strokeWidth="1.6" />
                </svg>
              </span>
              <div>
                <div className="text-sm font-medium text-text">Resources</div>
                <div className="text-xs text-text-muted">Books, papers, official sources, data & libraries.</div>
              </div>
            </GlassCard>
          </Link>
        </div>
      </Section>
    </MotionPage>
  );
}
