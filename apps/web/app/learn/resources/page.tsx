import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { LessonContent } from "@/app/learn/components/LessonContent";
import { readReferenceSource } from "@/app/learn/lib/content";

export const metadata: Metadata = { title: "Resources — Learn — QuantCouncil" };

export default function ResourcesPage() {
  const source = readReferenceSource("resources");
  if (!source) notFound();

  return (
    <MotionPage>
      <nav className="mb-4 text-xs text-text-faint">
        <Link href="/learn" className="hover:text-accent">
          Learn
        </Link>
        <span className="px-1.5">/</span>
        <span className="text-text-muted">Resources</span>
      </nav>
      <PageHeader
        title="Resources"
        subtitle="Books, papers, official sources, data, and libraries — no gurus, no shortcuts."
      />
      <div className="prose-learn">
        <LessonContent source={source} />
      </div>
    </MotionPage>
  );
}
