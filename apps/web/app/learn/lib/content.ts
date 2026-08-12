import fs from "fs";
import path from "path";

/**
 * Lesson bodies live as plain .mdx files under content/learn/, outside
 * app/ -- they're content, not routes. Read server-side only (fs/path are
 * Node built-ins; every caller of this module is a Server Component).
 */
const CONTENT_ROOT = path.join(process.cwd(), "content", "learn");

export function readLessonSource(moduleSlug: string, lessonSlug: string): string | null {
  const filePath = path.join(CONTENT_ROOT, moduleSlug, `${lessonSlug}.mdx`);
  if (!filePath.startsWith(CONTENT_ROOT)) return null; // guard against path traversal via params
  try {
    return fs.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}

export function readReferenceSource(slug: "glossary" | "resources"): string | null {
  const filePath = path.join(CONTENT_ROOT, `${slug}.mdx`);
  try {
    return fs.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}
