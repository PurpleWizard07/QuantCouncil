import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Fraunces } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";

import "./globals.css";

import { AppShell } from "./components/shell/AppShell";
import { ToastProvider } from "./components/ui/Toast";
import { MotionProvider } from "./components/ui/MotionProvider";

/**
 * The verdict voice -- reserved for risk/CIO decisions and hero numerals
 * only. SOFT and WONK are left at their default (0) so large-size verdict
 * type reads as a sharp engraved plate rather than the typeface's default
 * "wonky" editorial personality.
 */
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  axes: ["SOFT", "WONK", "opsz"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "QuantCouncil — AI Quant Command Center",
  description:
    "Personal AI quant research and paper-trading lab. Simulation only — no broker connectivity, no real orders.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable} ${fraunces.variable}`}
    >
      <body>
        <MotionProvider>
          <ToastProvider>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </MotionProvider>
      </body>
    </html>
  );
}
