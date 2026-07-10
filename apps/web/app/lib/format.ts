/**
 * Formatting helpers shared by every page. All numeric formatters are
 * null-safe: null/undefined/NaN render as the em-dash placeholder "—"
 * rather than "NaN", "null", or a blank string, so tables and metric cards
 * never show a broken-looking cell for a metric the backend didn't compute
 * (e.g. profit_factor with zero losing trades).
 */

const PLACEHOLDER = "—"; // —

type Num = number | null | undefined;

function isFiniteNumber(value: Num): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** Indian Rupees with Indian digit grouping (e.g. ₹12,34,567.89). */
export function fmtInr(value: Num, opts: { decimals?: number } = {}): string {
  if (!isFiniteNumber(value)) return PLACEHOLDER;
  const decimals = opts.decimals ?? 2;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Percentage formatter. Input is a fraction (0.1234 -> "12.34%") unless
 * `alreadyPercent` is set (12.34 -> "12.34%").
 */
export function fmtPct(
  value: Num,
  opts: { decimals?: number; alreadyPercent?: boolean; showSign?: boolean } = {},
): string {
  if (!isFiniteNumber(value)) return PLACEHOLDER;
  const decimals = opts.decimals ?? 2;
  const pct = opts.alreadyPercent ? value : value * 100;
  const sign = opts.showSign && pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(decimals)}%`;
}

/** Plain number with grouping (e.g. 1,234.5). */
export function fmtNum(value: Num, opts: { decimals?: number } = {}): string {
  if (!isFiniteNumber(value)) return PLACEHOLDER;
  const decimals = opts.decimals ?? 2;
  return new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/** Integer formatter with grouping, no decimals (e.g. trade counts). */
export function fmtInt(value: Num): string {
  if (!isFiniteNumber(value)) return PLACEHOLDER;
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);
}

/** ISO date ("YYYY-MM-DD" or full ISO datetime) -> "09 Jul 2026". */
export function fmtDate(value: string | null | undefined): string {
  if (!value) return PLACEHOLDER;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return PLACEHOLDER;
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

/** ISO datetime -> "09 Jul 2026, 14:05". */
export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return PLACEHOLDER;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return PLACEHOLDER;
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

/** UUID (or any id string) -> first 8 chars + ellipsis, for compact display. */
export function truncateId(id: string | null | undefined): string {
  if (!id) return PLACEHOLDER;
  return id.length <= 8 ? id : `${id.slice(0, 8)}…`;
}

export { PLACEHOLDER };
