import type { Heading } from "@/app/learn/lib/headings";

/** Static right-rail "on this page" nav, generated from the lesson's own
 * headings. Stickiness lives on the page's aside wrapper (shared with
 * MarginNote above it), not here. */
export function TableOfContents({ headings }: { headings: Heading[] }) {
  if (headings.length === 0) return null;
  return (
    <nav aria-label="On this page">
      <div className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-text-faint">On this page</div>
      <ul className="flex flex-col gap-1.5 border-l border-white/10 pl-3 text-sm">
        {headings.map((h) => (
          <li key={h.slug} className={h.depth === 3 ? "ml-3" : ""}>
            <a href={`#${h.slug}`} className="text-text-muted hover:text-accent">
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
