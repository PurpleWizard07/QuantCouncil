/** Cheap client- and server-safe reading-time estimate from raw MDX source. */

const WORDS_PER_MINUTE = 200;

export function estimateReadingMinutes(rawSource: string): number {
  const text = rawSource
    .replace(/```[\s\S]*?```/g, " ") // fenced code
    .replace(/\$\$[\s\S]*?\$\$/g, " ") // block math
    .replace(/<[^>]+>/g, " ") // jsx/html tags
    .replace(/[#>*_`|-]/g, " "); // markdown punctuation
  const words = text.split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}
