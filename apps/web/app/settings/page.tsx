"use client";

/**
 * Settings: read-only and honest. There are no client-mutable settings in
 * this app -- the API base URL is a build-time env var, the LLM provider
 * default is server-side, and there are (deliberately) no broker settings,
 * because there is no broker.
 */

import { GlassCard } from "@/app/components/ui/GlassCard";
import { MotionPage } from "@/app/components/ui/MotionPage";
import { PageHeader } from "@/app/components/ui/PageHeader";
import { Section } from "@/app/components/ui/Section";
import { API_BASE } from "@/app/lib/api";

interface ProviderRow {
  name: string;
  envVars: string;
  notes: string;
}

const PROVIDERS: ProviderRow[] = [
  {
    name: "mock",
    envVars: "none",
    notes: "Offline, deterministic, keyless. The default — everything works with zero credentials.",
  },
  {
    name: "auto",
    envVars: "none (resolves by priority)",
    notes: "Picks the first configured provider: anthropic > gemini > openrouter > ollama > mock.",
  },
  {
    name: "anthropic",
    envVars: "ANTHROPIC_API_KEY, ANTHROPIC_MODEL",
    notes: "Requires your own Anthropic API key.",
  },
  {
    name: "gemini",
    envVars: "GEMINI_API_KEY, GEMINI_MODEL",
    notes: "Requires your own Google Gemini API key.",
  },
  {
    name: "openrouter",
    envVars: "OPENROUTER_API_KEY, OPENROUTER_MODEL",
    notes: "Requires your own OpenRouter API key.",
  },
  {
    name: "ollama",
    envVars: "OLLAMA_BASE_URL, OLLAMA_MODEL",
    notes: "Local models via a running Ollama server; no cloud key needed.",
  },
];

export default function SettingsPage() {
  return (
    <MotionPage>
      <PageHeader
        title="Settings"
        subtitle="Read-only reference. Configuration lives in environment variables, not in this UI."
      />

      <Section title="Safety statement">
        <GlassCard variant="warning" padding="lg">
          <div className="flex items-start gap-4">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              className="mt-0.5 shrink-0 text-warning"
              aria-hidden="true"
            >
              <path d="M12 3l9 16H3L12 3z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
              <path d="M12 10v4M12 16.8v.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <div>
              <h3 className="text-sm font-semibold text-warning">Paper trading only — always</h3>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-text-muted">
                <li>This application has no broker connectivity of any kind.</li>
                <li>No real orders are ever placed; every fill is simulated against historical closes.</li>
                <li>All capital figures are virtual (default ₹10,00,000 simulated).</li>
                <li>Nothing in this application is financial advice.</li>
                <li>There are no broker settings on this page because no broker integration exists.</li>
              </ul>
            </div>
          </div>
        </GlassCard>
      </Section>

      <Section title="API connection">
        <GlassCard>
          <dl className="space-y-3 text-sm">
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <dt className="w-44 shrink-0 text-text-muted">API base URL in use</dt>
              <dd className="font-mono-ui text-accent">{API_BASE}</dd>
            </div>
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <dt className="w-44 shrink-0 text-text-muted">Configured by</dt>
              <dd className="text-text">
                <code className="font-mono-ui text-xs">NEXT_PUBLIC_API_URL</code>
                <span className="text-text-muted">
                  {" "}
                  — inlined at build time by Next.js; changing it requires a rebuild. Falls back to{" "}
                  <code className="font-mono-ui text-xs">http://localhost:8000</code>.
                </span>
              </dd>
            </div>
          </dl>
        </GlassCard>
      </Section>

      <Section
        title="AI committee providers"
        description="The effective default provider is set server-side via QUANTCOUNCIL_AGENT_PROVIDER (default: mock). Selecting an unconfigured provider fails loudly — it never silently falls back to mock."
      >
        <GlassCard padding="none" className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-text-muted">Provider</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Environment variables
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-text-muted">Notes</th>
              </tr>
            </thead>
            <tbody>
              {PROVIDERS.map((provider) => (
                <tr key={provider.name} className="border-b border-white/[0.05] last:border-0">
                  <td className="px-4 py-3 font-mono-ui text-accent">{provider.name}</td>
                  <td className="px-4 py-3 font-mono-ui text-xs text-text-muted">{provider.envVars}</td>
                  <td className="px-4 py-3 text-text-muted">{provider.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </GlassCard>
      </Section>

      <Section title="Documentation">
        <GlassCard>
          <p className="text-sm text-text-muted">Reference docs live in the repository:</p>
          <ul className="mt-2 space-y-1 font-mono-ui text-xs text-text">
            <li>.env.example — every environment variable, with comments</li>
            <li>docs/strategy-format.md — the strategy definition schema</li>
            <li>docs/paper-trading-design.md — paper engine rules incl. “No Real Orders — Ever”</li>
            <li>README.md — project overview and setup</li>
          </ul>
        </GlassCard>
      </Section>
    </MotionPage>
  );
}
