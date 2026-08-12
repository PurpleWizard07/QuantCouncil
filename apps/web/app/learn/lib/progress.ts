/**
 * Lesson-completion tracking. QuantCouncil has no user/auth system anywhere
 * in the stack (single Postgres instance, zero sessions) -- so progress is
 * scoped honestly to this browser via localStorage, not oversold as
 * account-synced. If multi-device sync is ever wanted, that's a product
 * decision to add accounts at all, not something Learn should force.
 */

const STORAGE_KEY = "qc:learn:progress";

function readSet(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? new Set(parsed) : new Set();
  } catch {
    return new Set();
  }
}

function writeSet(set: Set<string>): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(set)));
}

export function isLessonComplete(id: string): boolean {
  return readSet().has(id);
}

export function setLessonComplete(id: string, complete: boolean): void {
  const set = readSet();
  if (complete) set.add(id);
  else set.delete(id);
  writeSet(set);
  window.dispatchEvent(new CustomEvent("qc:learn:progress-changed"));
}

export function completedCount(ids: string[]): number {
  const set = readSet();
  return ids.filter((id) => set.has(id)).length;
}

export const PROGRESS_EVENT = "qc:learn:progress-changed";
