import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

import { AppShell } from "./components/shell/AppShell";
import { ToastProvider } from "./components/ui/Toast";

export const metadata: Metadata = {
  title: "QuantCouncil — AI Quant Command Center",
  description:
    "Personal AI quant research and paper-trading lab. Simulation only — no broker connectivity, no real orders.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ToastProvider>
          <AppShell>{children}</AppShell>
        </ToastProvider>
      </body>
    </html>
  );
}
