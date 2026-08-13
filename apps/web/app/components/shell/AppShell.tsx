"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";

import { getHealth } from "@/app/lib/api";

import { CommandPalette } from "./CommandPalette";
import { NAV_GROUPS, labelForPathname } from "./nav";

type HealthStatus = "checking" | "online" | "offline";

const HEALTH_POLL_MS = 30_000;

function useApiHealth(): HealthStatus {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        await getHealth();
        if (!cancelled) setStatus("online");
      } catch {
        if (!cancelled) setStatus("offline");
      }
    }

    check();
    const timer = setInterval(check, HEALTH_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return status;
}

/** A recessed tell-tale lamp, not a plain dot -- an inset ring sells the
 * "light behind a bezel" read rather than a flat colored circle. */
function ApiHealthIndicator() {
  const status = useApiHealth();
  const lampClass =
    status === "online"
      ? "bg-positive shadow-[0_0_6px_1px_rgba(52,178,122,0.7)] animate-pulse-glow"
      : status === "offline"
        ? "bg-negative shadow-[0_0_6px_1px_rgba(225,92,110,0.6)]"
        : "bg-text-faint";
  const label = status === "online" ? "API online" : status === "offline" ? "API offline" : "Checking…";
  const textClass =
    status === "online" ? "text-positive" : status === "offline" ? "text-negative" : "text-text-faint";

  return (
    <span className="flex items-center gap-2 text-xs font-medium" title="Polled every 30s">
      <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-black/40 shadow-[inset_0_1px_2px_rgba(0,0,0,0.6)]">
        <span className={`h-1.5 w-1.5 rounded-full ${lampClass}`} aria-hidden="true" />
      </span>
      <span className={`hidden sm:inline ${textClass}`}>{label}</span>
    </span>
  );
}

function PaperOnlyBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/40 bg-warning-soft px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-warning">
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M12 3l9 16H3L12 3z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path d="M12 10v4M12 16.8v.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      Paper trading only — simulated
    </span>
  );
}

/** `layoutId` shares this element across every render of the active link,
 * so Motion animates it sliding to the new position instead of the old
 * indicator fading out while a new one fades in elsewhere. */
function ActiveTravelingLight({ layoutId }: { layoutId: string }) {
  return (
    <motion.span
      layoutId={layoutId}
      transition={{ type: "spring", stiffness: 380, damping: 32, mass: 0.9 }}
      className="absolute -left-3 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-accent shadow-[0_0_8px_rgba(76,195,217,0.8)]"
      aria-hidden="true"
    />
  );
}

function SidebarNav({ onNavigate, lightLayoutId }: { onNavigate?: () => void; lightLayoutId: string }) {
  const pathname = usePathname();

  function isActive(href: string): boolean {
    return href === "/"
      ? pathname === "/" || pathname === "/dashboard"
      : pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-3" aria-label="Primary">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <div className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-text-faint">
            {group.label}
          </div>
          <div className="flex flex-col gap-0.5">
            {group.items.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className={`group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    active
                      ? "bg-accent-soft font-medium text-accent"
                      : "text-text-muted hover:bg-white/[0.04] hover:text-text"
                  }`}
                >
                  {active && <ActiveTravelingLight layoutId={lightLayoutId} />}
                  <span className={active ? "text-accent" : "text-text-faint group-hover:text-text-muted"}>
                    {item.icon}
                  </span>
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

function SidebarContent({ onNavigate, lightLayoutId }: { onNavigate?: () => void; lightLayoutId: string }) {
  return (
    <>
      <div className="mb-6 px-6 pt-6">
        <Link href="/" onClick={onNavigate} className="block">
          <div className="text-lg font-bold tracking-tight text-text">
            Quant<span className="text-accent text-glow-accent">Council</span>
          </div>
          <div className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-text-faint">
            AI quant command center
          </div>
        </Link>
      </div>
      <SidebarNav onNavigate={onNavigate} lightLayoutId={lightLayoutId} />
      <div className="border-t border-white/[0.06] px-6 py-4 text-[11px] leading-relaxed text-text-faint">
        Simulation only.
        <br />
        No broker. No real money.
      </div>
    </>
  );
}

/**
 * The persistent app shell: fixed solid-graphite sidebar, grouped into
 * Council / Library / System (collapsing to a hamburger drawer below lg),
 * top command bar (breadcrumb, ⌘K palette, API health lamp, paper-only
 * badge), and the max-width content container.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[264px] flex-col border-r border-white/[0.08] bg-bg-raised lg:flex">
        <SidebarContent lightLayoutId="sidebar-active-light-desktop" />
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            />
            <motion.aside
              key="drawer"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              className="fixed inset-y-0 left-0 z-50 flex w-[264px] flex-col border-r border-white/[0.08] bg-bg-raised lg:hidden"
            >
              <SidebarContent onNavigate={() => setMobileOpen(false)} lightLayoutId="sidebar-active-light-mobile" />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main column */}
      <div className="flex min-h-screen flex-col lg:pl-[264px]">
        {/* Command bar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-white/[0.08] bg-bg-raised px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="rounded-lg p-2 text-text-muted hover:bg-white/[0.06] hover:text-text lg:hidden"
              aria-label="Open navigation"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
            <div className="flex items-baseline gap-2 text-sm">
              <span className="hidden text-text-faint sm:inline">QuantCouncil</span>
              <span className="hidden text-text-faint sm:inline" aria-hidden="true">
                /
              </span>
              <span className="font-medium text-text">{labelForPathname(pathname)}</span>
            </div>
          </div>
          <div className="flex items-center gap-3 sm:gap-4">
            <CommandPalette />
            <ApiHealthIndicator />
            <PaperOnlyBadge />
          </div>
        </header>

        {/* Page content */}
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
