import type { ReactNode } from "react";

export interface NavItem {
  label: string;
  href: string;
  icon: ReactNode;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

/**
 * Inline SVG icons -- no icon library, per the foundation brief. Grouped
 * into the building's three rooms: Council (the deliberation/evidence/
 * execution loop), Library (the reading room), System (account-level config).
 */
export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Council",
    items: [
      {
        label: "Dashboard",
        href: "/",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <rect x="3" y="3" width="7.5" height="7.5" rx="1.5" />
            <rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5" />
            <rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5" />
            <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5" />
          </svg>
        ),
      },
      {
        label: "Research",
        href: "/research",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <circle cx="11" cy="11" r="6.5" />
            <path d="M20.5 20.5l-4.8-4.8" />
            <path d="M11 8v6M8 11h6" />
          </svg>
        ),
      },
      {
        label: "Market",
        href: "/market",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <path d="M3 17l5.5-5.5 4 4L21 7" />
            <path d="M15.5 7H21v5.5" />
          </svg>
        ),
      },
      {
        label: "Strategies",
        href: "/strategies",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
            <circle cx="12" cy="12" r="4" />
          </svg>
        ),
      },
      {
        label: "Backtests",
        href: "/backtests",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <circle cx="12" cy="12" r="8.5" />
            <path d="M12 7.5V12l3 2" />
          </svg>
        ),
      },
      {
        label: "Risk",
        href: "/risk",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <path d="M12 3l8 3.5v5c0 4.5-3.2 8-8 9.5-4.8-1.5-8-5-8-9.5v-5L12 3z" />
            <path d="M12 8.5v4M12 15.8v.2" />
          </svg>
        ),
      },
      {
        label: "AI Committee",
        href: "/committee",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <circle cx="8" cy="9" r="3" />
            <circle cx="16.5" cy="9.5" r="2.5" />
            <path d="M3 19c.5-3 2.5-4.5 5-4.5s4.5 1.5 5 4.5" />
            <path d="M14.5 14.8c2.6-.4 5.6.7 6.5 4.2" />
          </svg>
        ),
      },
      {
        label: "Paper Portfolio",
        href: "/paper",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <rect x="3" y="6" width="18" height="14" rx="2" />
            <path d="M8 6V4.5A1.5 1.5 0 0 1 9.5 3h5A1.5 1.5 0 0 1 16 4.5V6" />
            <path d="M3 12h18" />
          </svg>
        ),
      },
      {
        label: "Journal",
        href: "/journal",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v18H6.5A1.5 1.5 0 0 1 5 19.5v-15z" />
            <path d="M9 7.5h6M9 11h6" />
          </svg>
        ),
      },
    ],
  },
  {
    label: "Library",
    items: [
      {
        label: "Learn",
        href: "/learn",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <path d="M3 5.5c2.3-1.1 5.4-1 8 .4v13.1c-2.6-1.4-5.7-1.5-8-.4z" />
            <path d="M21 5.5c-2.3-1.1-5.4-1-8 .4v13.1c2.6-1.4 5.7-1.5 8-.4z" />
          </svg>
        ),
      },
    ],
  },
  {
    label: "System",
    items: [
      {
        label: "Settings",
        href: "/settings",
        icon: (
          <svg width="17" height="17" viewBox="0 0 24 24" {...stroke}>
            <circle cx="12" cy="12" r="3" />
            <path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L14.2 3h-4l-.4 2.7a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5a7 7 0 0 0 0 2.4l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2l.4 2.7h4l.4-2.7a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5c.06-.4.1-.8.1-1.2z" />
          </svg>
        ),
      },
    ],
  },
];

/** Flattened item list -- for lookups that don't care about grouping. */
export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((group) => group.items);

/** The nav label for a pathname, used by the command-bar breadcrumb. */
export function labelForPathname(pathname: string): string {
  if (pathname === "/" || pathname === "/dashboard") return "Dashboard";
  const match = NAV_ITEMS.filter((item) => item.href !== "/").find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
  return match?.label ?? "QuantCouncil";
}
