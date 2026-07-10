import type { StrategyRecord } from "@/app/lib/types";

/**
 * Best-effort extraction of "entry"/"exit" condition-tree shapes per
 * docs/strategy-format.md. The shared StrategyRecord type intentionally
 * types entry_rules/exit_rules as `unknown` (rule internals are loose), so
 * this walker defends against any shape rather than assuming one.
 */
interface ConditionLike {
  indicator?: string;
  params?: { window?: number };
  target?: { indicator?: string; params?: { window?: number } };
  all?: unknown[];
  any?: unknown[];
}

function labelFor(indicator?: string, window?: number): string | null {
  if (!indicator) return null;
  return typeof window === "number" ? `${indicator}(${window})` : indicator;
}

function walk(node: unknown, out: string[]): void {
  if (!node || typeof node !== "object") return;
  const n = node as ConditionLike;
  if (Array.isArray(n.all)) {
    n.all.forEach((child) => walk(child, out));
    return;
  }
  if (Array.isArray(n.any)) {
    n.any.forEach((child) => walk(child, out));
    return;
  }
  const left = labelFor(n.indicator, n.params?.window);
  if (left) out.push(left);
  if (n.target) {
    const right = labelFor(n.target.indicator, n.target.params?.window);
    if (right) out.push(right);
  }
}

/** Extracts a de-duplicated list of indicator labels (e.g. "sma(20)") from a condition tree. */
export function summarizeRuleTree(tree: unknown): string[] {
  const out: string[] = [];
  walk(tree, out);
  return Array.from(new Set(out));
}

/**
 * The API's field names for rule trees aren't 100% pinned down by the shared
 * type (it only guarantees `entry_rules`/`exit_rules` keys exist as
 * `unknown`), so this also falls back to the doc-named `entry`/`exit` keys
 * via the record's index signature -- never guessing at new top-level shape,
 * just tolerating either name for the same tree.
 */
export function summarizeStrategyRules(strategy: StrategyRecord): { entry: string[]; exit: string[] } {
  const entryTree = strategy.entry_rules ?? (strategy as Record<string, unknown>)["entry"];
  const exitTree = strategy.exit_rules ?? (strategy as Record<string, unknown>)["exit"];
  return { entry: summarizeRuleTree(entryTree), exit: summarizeRuleTree(exitTree) };
}
