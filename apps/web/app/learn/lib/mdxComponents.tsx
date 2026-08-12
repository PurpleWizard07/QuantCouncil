import type { ComponentProps } from "react";

import { CollapsibleSection } from "@/app/components/ui/CollapsibleSection";
import { Callout } from "@/app/learn/components/Callout";
import { PayoffDiagram } from "@/app/learn/components/PayoffDiagram";
import { Pipeline, Step } from "@/app/learn/components/Pipeline";
import { Quiz } from "@/app/learn/components/Quiz";
import { Term } from "@/app/learn/components/Term";

/**
 * Elements available inside every lesson MDX file: standard prose tags get a
 * dark-theme pass (blockquote, table, code), and the custom lesson
 * components (Callout, Quiz, PayoffDiagram, Pipeline, Term) are exposed by
 * name so content can use `<Callout>`, `<Quiz>`, etc. directly.
 */
export const mdxComponents = {
  blockquote: (props: ComponentProps<"blockquote">) => (
    <blockquote
      className="my-4 border-l-[3px] border-accent/40 pl-4 text-text-muted italic [&_p]:mb-2 [&_p:last-child]:mb-0"
      {...props}
    />
  ),
  table: (props: ComponentProps<"table">) => (
    <div className="my-5 overflow-x-auto rounded-lg border border-white/10">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  thead: (props: ComponentProps<"thead">) => <thead className="bg-white/[0.04]" {...props} />,
  th: (props: ComponentProps<"th">) => (
    <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-text-faint" {...props} />
  ),
  td: (props: ComponentProps<"td">) => <td className="border-b border-white/[0.06] px-3 py-2 align-top text-text-muted" {...props} />,
  code: (props: ComponentProps<"code">) => <code className="font-mono-ui rounded bg-white/[0.06] px-1 py-0.5 text-[0.9em] text-accent-2" {...props} />,
  pre: (props: ComponentProps<"pre">) => (
    <pre className="font-mono-ui my-4 overflow-x-auto rounded-xl border border-white/10 bg-black/30 p-4 text-[13px] leading-relaxed text-text [&_code]:bg-transparent [&_code]:p-0 [&_code]:text-text" {...props} />
  ),
  a: (props: ComponentProps<"a">) => <a className="text-accent underline underline-offset-2 hover:text-accent-2" {...props} />,
  hr: () => <hr className="my-8 border-white/10" />,
  Callout,
  Quiz,
  PayoffDiagram,
  Pipeline,
  Step,
  Term,
  CollapsibleSection,
};
