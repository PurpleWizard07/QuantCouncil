"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";

import { DURATION, EASE } from "@/app/lib/motion";

import { NAV_GROUPS } from "./nav";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
/** Deliberately strict: only an already-uppercase token reads as a pasted
 * ticker (NSE convention). A lowercase query like "market" should search
 * nav labels, not get treated as the literal symbol "MARKET". */
const TICKER_RE = /^[A-Z][A-Z0-9&-]{1,19}$/;

interface PaletteAction {
  key: string;
  label: string;
  hint: string;
  onSelect: () => void;
}

/**
 * Global ⌘K / Ctrl+K palette: fuzzy-jump to any nav destination, or paste a
 * raw backtest_id / risk_evaluation_id / ticker and jump straight to it.
 * IDs are opaque UUIDs with no distinguishing shape, so a pasted UUID offers
 * both candidate destinations rather than guessing.
 *
 * The one deliberately floating surface in the app -- real .glass blur, not
 * .surface -- since it sits transiently above whatever page is underneath.
 */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(0);
    const raf = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(raf);
  }, [open]);

  function go(href: string) {
    router.push(href);
    setOpen(false);
  }

  const navActions: PaletteAction[] = useMemo(
    () =>
      NAV_GROUPS.flatMap((group) =>
        group.items.map((item) => ({
          key: `nav:${item.href}`,
          label: item.label,
          hint: group.label,
          onSelect: () => go(item.href),
        })),
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const trimmed = query.trim();

  const recordActions: PaletteAction[] = [];
  if (UUID_RE.test(trimmed)) {
    recordActions.push(
      {
        key: "record:backtest",
        label: `Open as backtest`,
        hint: trimmed,
        onSelect: () => go(`/backtests?backtest_id=${trimmed}`),
      },
      {
        key: "record:risk",
        label: `Open as risk evaluation`,
        hint: trimmed,
        onSelect: () => go(`/risk?risk_evaluation_id=${trimmed}`),
      },
    );
  } else if (TICKER_RE.test(trimmed)) {
    recordActions.push({
      key: "record:symbol",
      label: `Open ${trimmed} in Market`,
      hint: "Market",
      onSelect: () => go(`/market?symbol=${trimmed}`),
    });
  }

  const filteredNav = trimmed
    ? navActions.filter((a) => a.label.toLowerCase().includes(trimmed.toLowerCase()))
    : navActions;

  const results = [...recordActions, ...filteredNav];

  function onInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      results[activeIndex]?.onSelect();
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-text-faint transition-colors hover:border-white/20 hover:text-text-muted"
        aria-label="Open command palette"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.8" />
          <path d="M20.5 20.5l-4.8-4.8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        <span className="hidden sm:inline">Jump to…</span>
        <kbd className="hidden rounded border border-white/10 bg-white/[0.04] px-1.5 py-0.5 font-mono-ui text-[10px] text-text-faint sm:inline">
          ⌘K
        </kbd>
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              key="palette-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: DURATION.element }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              key="palette"
              role="dialog"
              aria-modal="true"
              aria-label="Command palette"
              initial={{ opacity: 0, y: -12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -12, scale: 0.98 }}
              transition={{ duration: DURATION.surface, ease: EASE }}
              className="glass fixed left-1/2 top-[14vh] z-[61] w-[min(560px,calc(100vw-2rem))] -translate-x-1/2 overflow-hidden rounded-2xl"
            >
              <div className="flex items-center gap-2.5 border-b border-white/[0.08] px-4 py-3">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="shrink-0 text-text-faint">
                  <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M20.5 20.5l-4.8-4.8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setActiveIndex(0);
                  }}
                  onKeyDown={onInputKeyDown}
                  placeholder="Jump to a page, or paste a backtest / risk / ticker id…"
                  className="w-full bg-transparent text-sm text-text placeholder:text-text-faint outline-none"
                />
                <kbd className="shrink-0 rounded border border-white/10 bg-white/[0.04] px-1.5 py-0.5 font-mono-ui text-[10px] text-text-faint">
                  esc
                </kbd>
              </div>

              <div className="max-h-[min(60vh,420px)] overflow-y-auto p-2">
                {results.length === 0 ? (
                  <p className="px-3 py-6 text-center text-sm text-text-faint">No matches.</p>
                ) : (
                  results.map((action, i) => (
                    <button
                      key={action.key}
                      type="button"
                      onClick={action.onSelect}
                      onMouseEnter={() => setActiveIndex(i)}
                      className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                        i === activeIndex ? "bg-accent-soft text-accent" : "text-text hover:bg-white/[0.04]"
                      }`}
                    >
                      <span className="truncate font-medium">{action.label}</span>
                      <span className="shrink-0 font-mono-ui text-[11px] text-text-faint">{action.hint}</span>
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
