import type { JournalEntry } from "@/app/lib/types";

/**
 * PaperOrder/PaperPosition (see app/lib/types.ts) only carry a numeric
 * `asset_id` -- there is NO symbol string on either record, and AssetRecord
 * (GET /assets) has no numeric id to join against, so the frontend cannot
 * resolve asset_id -> symbol directly. This is a real gap between the page
 * spec (which assumed a `symbol` field) and the actual API contract; do not
 * invent a field that doesn't exist.
 *
 * Workaround: apps/api/app/services/paper_engine.py stamps the human symbol
 * into every FILL/RISK_EVENT journal entry's `refs.symbol`, and every order
 * and position has a corresponding journal entry linked via `order_id`/
 * `position_id`. So we reconstruct the join client-side from the portfolio's
 * journal feed (already-typed `getJournal`), falling back to "#<asset_id>"
 * for any id the journal hasn't covered yet (e.g. a brand new REJECTED order
 * whose own journal entry -- written in the same request -- should already
 * carry it, but we stay defensive regardless).
 */
export interface SymbolMaps {
  byOrderId: Record<string, string>;
  byPositionId: Record<string, string>;
}

export function buildSymbolMaps(journal: JournalEntry[]): SymbolMaps {
  const byOrderId: Record<string, string> = {};
  const byPositionId: Record<string, string> = {};

  for (const entry of journal) {
    const refs = entry.refs;
    const symbol = refs && typeof refs.symbol === "string" ? (refs.symbol as string) : undefined;
    if (!symbol) continue;
    if (entry.order_id) byOrderId[entry.order_id] = symbol;
    if (entry.position_id) byPositionId[entry.position_id] = symbol;
  }

  return { byOrderId, byPositionId };
}

export function symbolForOrder(maps: SymbolMaps, orderId: string, assetId: number): string {
  return maps.byOrderId[orderId] ?? `#${assetId}`;
}

export function symbolForPosition(maps: SymbolMaps, positionId: string, assetId: number): string {
  return maps.byPositionId[positionId] ?? `#${assetId}`;
}
