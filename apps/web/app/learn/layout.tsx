import type { ReactNode } from "react";

import "katex/dist/katex.min.css";

/**
 * Scopes the KaTeX stylesheet to /learn/** only -- nothing outside Learn
 * renders math, so this import shouldn't ship on every route in the app.
 *
 * `.learn-room` retints every color token for this subtree -- the reading
 * room's warm paper tones, distinct from the rest of the app's graphite --
 * without any component underneath needing its own styling changes.
 */
export default function LearnLayout({ children }: { children: ReactNode }) {
  return <div className="learn-room">{children}</div>;
}
