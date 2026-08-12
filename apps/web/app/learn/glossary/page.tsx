import Link from "next/link";
import type { Metadata } from "next";

import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { GlossarySearch } from "@/app/learn/components/GlossarySearch";

export const metadata: Metadata = { title: "Glossary — Learn — QuantCouncil" };

export default function GlossaryPage() {
  return (
    <MotionPage>
      <nav className="mb-4 text-xs text-text-faint">
        <Link href="/learn" className="hover:text-accent">
          Learn
        </Link>
        <span className="px-1.5">/</span>
        <span className="text-text-muted">Glossary</span>
      </nav>
      <PageHeader
        title="Glossary"
        subtitle="Every term used across the curriculum: a simple definition, a technical one, and a worked example."
      />
      <GlossarySearch />
    </MotionPage>
  );
}
