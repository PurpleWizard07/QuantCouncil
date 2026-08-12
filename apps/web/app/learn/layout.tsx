import type { ReactNode } from "react";

import "katex/dist/katex.min.css";

/**
 * Scopes the KaTeX stylesheet to /learn/** only -- nothing outside Learn
 * renders math, so this import shouldn't ship on every route in the app.
 */
export default function LearnLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
