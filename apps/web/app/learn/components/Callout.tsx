import type { ReactNode } from "react";

import { VARIANT_STYLES, type StatusVariant } from "@/app/components/ui/variants";

export type CalloutType = "info" | "warning" | "success" | "danger";

const TYPE_TO_VARIANT: Record<CalloutType, StatusVariant> = {
  info: "watchlist",
  warning: "warning",
  success: "positive",
  danger: "negative",
};

const ICONS: Record<CalloutType, ReactNode> = {
  info: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 11v5M12 8v.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
  warning: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M12 3l9 16H3L12 3z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M12 10v4M12 16.8v.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
  success: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path d="M8 12.5l2.5 2.5L16 9.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  danger: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M12 3l9 16H3L12 3z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M12 10v4M12 16.8v.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
};

export interface CalloutProps {
  type?: CalloutType;
  title?: string;
  children: ReactNode;
}

/**
 * Structural callout for lesson content -- the "educational only" derivatives
 * banner, product bridges, and any new emphasis block. Built directly on the
 * existing VARIANT_STYLES vocabulary so it tints identically to every other
 * status surface in the app. The source's own inline 💡/⚠️/🤔/🔬 microformats
 * stay as plain blockquotes (styled in the prose stylesheet) -- this
 * component is reserved for new structural banners, not a content rewrite.
 */
export function Callout({ type = "info", title, children }: CalloutProps) {
  const style = VARIANT_STYLES[TYPE_TO_VARIANT[type]];
  return (
    <div
      className={`my-5 rounded-xl border px-4 py-3.5 text-sm leading-relaxed ${style.border} ${style.bg}`}
      role="note"
    >
      <div className="flex gap-2.5">
        <span className={`mt-0.5 shrink-0 ${style.text}`} aria-hidden="true">
          {ICONS[type]}
        </span>
        <div className="min-w-0 text-text-muted [&_p]:mb-2 [&_p:last-child]:mb-0 [&_a]:underline [&_a]:underline-offset-2">
          {title && <div className={`mb-1 font-semibold ${style.text}`}>{title}</div>}
          {children}
        </div>
      </div>
    </div>
  );
}
