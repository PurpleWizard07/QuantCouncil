import GithubSlugger from "github-slugger";

export interface Heading {
  depth: 2 | 3;
  text: string;
  slug: string;
}

/**
 * Extracts ## and ### headings from raw MDX source for the "on this page"
 * nav, using github-slugger -- the same slugger rehype-slug uses internally
 * -- so these ids are guaranteed to match the ones actually rendered.
 */
export function extractHeadings(rawSource: string): Heading[] {
  const slugger = new GithubSlugger();
  const headings: Heading[] = [];
  const lines = rawSource.split("\n");
  let inCodeFence = false;

  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      inCodeFence = !inCodeFence;
      continue;
    }
    if (inCodeFence) continue;

    const match = /^(#{2,3})\s+(.+?)\s*$/.exec(line);
    if (!match) continue;
    const depth = match[1].length as 2 | 3;
    const text = match[2].replace(/[*_`]/g, "").trim();
    if (!text) continue;
    headings.push({ depth, text, slug: slugger.slug(text) });
  }

  return headings;
}
