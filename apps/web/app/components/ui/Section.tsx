"use client";

import type { ReactNode } from "react";

export interface SectionProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** A titled block of content -- the standard way to group cards on a page. */
export function Section({ title, description, actions, children, className = "" }: SectionProps) {
  return (
    <section className={`mb-8 ${className}`}>
      {(title || actions) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            {title && (
              <h2 className="text-xs font-semibold uppercase tracking-widest text-text-muted">
                {title}
              </h2>
            )}
            {description && <p className="mt-1 text-sm text-text-muted">{description}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
