"use client";

import { useState } from "react";

export interface JsonViewerProps {
  data: unknown;
  label?: string;
  collapsed?: boolean;
  className?: string;
}

/** Collapsible, pretty-printed JSON in the mono font -- for raw audit payloads. */
export function JsonViewer({ data, label = "JSON", collapsed = false, className = "" }: JsonViewerProps) {
  const [open, setOpen] = useState(!collapsed);

  return (
    <div className={`glass rounded-xl ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left"
        aria-expanded={open}
      >
        <span className="font-mono-ui text-xs font-medium text-text-muted">{label}</span>
        <span className="text-xs text-text-faint">{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <pre className="max-h-96 overflow-auto border-t border-white/[0.06] px-4 py-3 font-mono-ui text-[12px] leading-relaxed text-text/90">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
