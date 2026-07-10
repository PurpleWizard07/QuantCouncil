# QuantCouncil AI Committee (Phase 6)

The authoritative reference for the Phase 6 AI Committee: agent architecture, role definitions,
strict JSON outputs, deterministic veto binding, and API surface. Component boundaries are
defined in [architecture.md](architecture.md); the delivery history and deviations from the
original plan are in [development-roadmap.md](development-roadmap.md); the underlying engineering
decisions are logged in [assumptions.md](assumptions.md).

Everything in this layer is optional and LLM-based (`packages/agents`) with **zero computation**
— agents reason and debate, they never invent metrics or override the risk engine's verdict.
**No LLM touches, computes, or produces any number here** — every figure cited comes verbatim
from deterministic inputs (backtest metrics, risk evaluation, trade summary). The system
degrades gracefully when LLM credentials are absent (mock provider, offline, always available).

## Philosophy: "AI Can Propose. Math Can Approve. Risk Can Veto."

The AI committee proposes strategies, reasons about them, and issues a decision. The risk engine
approves or rejects — deterministically, without LLM involvement. If the risk engine rejects,
the CIO agent **cannot** decide `PAPER_TRADE` — this constraint is **enforced by code** (a
Pydantic validator in `packages/agents`), not by prompt. The committee never creates paper orders:
that is a manual endpoint (`POST /paper/orders`) where the veto is enforced a second time.

## Committee Architecture

### Six Agents, Strict Pydantic Schemas

The committee runs six agents in sequence; each receives the outputs of previous agents
(`committee_so_far` in their payload). Every agent output is validated against a strict Pydantic
schema with `extra="forbid"` (no unknown fields). Responses are persisted before the next agent
runs.

| Role | Input | Output Schema | Note |
|---|---|---|---|
| **Technical Analyst** | Backtest metrics, indicators, signals summary | `view` (BULLISH/BEARISH/NEUTRAL/MIXED), `confidence` [0,1], `signals[]`, `warnings[]`, `summary` | Reads chart/momentum patterns |
| **Quant Researcher** | Strategy rule set, metrics, ratios | `strategy_quality` (STRONG/ACCEPTABLE/WEAK/INVALID), `rule_interpretation`, `strengths[]`, `weaknesses[]`, `improvement_ideas[]`, `summary` | Never recomputes metrics; interprets only |
| **Bull** | Backtest results, thesis, upside scenarios | `case_strength` [0,1], `arguments[]`, `best_case_scenario`, `summary` | Argues the bullish case |
| **Bear** | Backtest results, downside risks, failure modes | `case_strength` [0,1], `risks[]`, `failure_modes[]`, `worst_case_scenario`, `summary` | Argues the bearish case |
| **Risk Narrator** | Deterministic risk verdict, failed rules, warnings | `risk_summary`, `failed_rules_explained[]`, `warnings_explained[]`, `plain_english_verdict` | Narrates risk; never alters it |
| **CIO** (raw) | All prior agents, backtest, risk verdict | `decision` (PAPER_TRADE/NO_TRADE/WATCHLIST), `summary`, `reason`, `conditions_to_reconsider[]` | **Never receives `approved_by_risk` field** |

### Committee Flow

```
1. Persist backtest_id + risk_evaluation_id
   ↓
2. Load persisted backtest metrics and risk evaluation (404 if unknown or mismatch)
   ↓
3. Build deterministic context:
   - Strategy definition
   - All backtest metrics (total_return, max_drawdown, win_rate, profit_factor, etc.)
   - Risk verdict (APPROVED/REJECTED/NEEDS_REVIEW, risk_score)
   - List of trades (entry/exit dates, P&L)
   - Symbol and date range
   ↓
4. Run agents in order, accumulating committee_so_far:
   a. Technical Analyst → output + persist
   b. Quant Researcher → output + persist
   c. Bull → output + persist
   d. Bear → output + persist
   e. Risk Narrator → output + persist
   f. CIO (raw) → output + persist (stored without approved_by_risk)
   ↓
5. Apply code-level veto:
   - Copy approved_by_risk FROM the persisted risk evaluation (code sets this)
   - If approved_by_risk=false AND raw CIO said PAPER_TRADE → override to NO_TRADE
   - Record exact audit warning: "CIO raw PAPER_TRADE overridden because risk engine rejected the backtest."
   ↓
6. Build final CIODecision (with approved_by_risk, model, override_warning, audit_refs)
   ↓
7. Validate final CIODecision (Pydantic):
   - Reject if approved_by_risk=false AND decision=PAPER_TRADE
   - This is an independent, structural enforcement layer
   ↓
8. Persist final CIODecision (row 7 of 7)
   ↓
9. Return all outputs (raw CIO + final CIO + all prior agents + refs)
```

### Agent Role Output Schemas

**Technical Analyst:**
```json
{
  "view": "BULLISH|BEARISH|NEUTRAL|MIXED",
  "confidence": 0.0-1.0,
  "signals": ["signal 1", "signal 2"],
  "warnings": ["warning 1"],
  "summary": "Plain English summary"
}
```

**Quant Researcher:**
```json
{
  "strategy_quality": "STRONG|ACCEPTABLE|WEAK|INVALID",
  "rule_interpretation": "How well the rules translate to the backtest results",
  "strengths": ["strength 1"],
  "weaknesses": ["weakness 1"],
  "improvement_ideas": ["idea 1"],
  "summary": "Plain English summary"
}
```

**Bull:**
```json
{
  "case_strength": 0.0-1.0,
  "arguments": ["argument 1"],
  "best_case_scenario": "Description of upside scenario",
  "summary": "Plain English summary"
}
```

**Bear:**
```json
{
  "case_strength": 0.0-1.0,
  "risks": ["risk 1"],
  "failure_modes": ["failure mode 1"],
  "worst_case_scenario": "Description of downside scenario",
  "summary": "Plain English summary"
}
```

**Risk Narrator:**
```json
{
  "risk_summary": "Risk evaluation conclusion",
  "failed_rules_explained": ["rule and explanation"],
  "warnings_explained": ["warning and explanation"],
  "plain_english_verdict": "APPROVED / REJECTED / NEEDS_REVIEW and why"
}
```

**CIO (raw, untrusted):**
```json
{
  "decision": "PAPER_TRADE|NO_TRADE|WATCHLIST",
  "summary": "Why this decision",
  "reason": "Plain English reasoning",
  "conditions_to_reconsider": ["condition to monitor or review"]
}
```
Note: Raw CIO has **NO `approved_by_risk` field**. The field is added by code only in the final output.

**CIODecision (final, after veto override):**
```json
{
  "decision": "PAPER_TRADE|NO_TRADE|WATCHLIST",
  "summary": "Why this decision",
  "reason": "Plain English reasoning",
  "conditions_to_reconsider": ["condition to monitor or review"],
  "approved_by_risk": true|false,
  "override_warning": null|"CIO raw PAPER_TRADE overridden because risk engine rejected the backtest."
}
```

The final `CIODecision` passes through a Pydantic validator that rejects `approved_by_risk=false` + `decision=PAPER_TRADE`.

## The Risk-Veto Binding (Two-Layer Enforcement)

### Layer 1: Code-Level Override

Code in `packages/agents/agents/committee.py` (function `run_committee`) applies the veto:

```python
# After the raw CIO agent runs:
approved_by_risk = risk_evaluation.approved  # Code copies this
if approved_by_risk is False and cio_raw.decision == "PAPER_TRADE":
    final_decision = "NO_TRADE"
    override_warning = "CIO raw PAPER_TRADE overridden because risk engine rejected the backtest."
else:
    final_decision = cio_raw.decision
    override_warning = None
```

The override is **not silent** — the audit warning is persisted and visible in the response.

### Layer 2: Schema Validator

The `CIODecision` Pydantic model includes a validator that structurally rejects any instance with
`approved_by_risk=false` AND `decision=PAPER_TRADE`, raising a validation error before persistence.

This validator exists independently and was present since Phase 1 (in the risk-engine design);
it is unchanged in Phase 6.

### Why Two Layers?

1. **Code override** ensures the database row is never created with contradictory state, AND
   provides an audit trail (the warning is persisted).
2. **Schema validator** catches programming errors: if code mistakenly tries to persist a
   contradictory state, the Pydantic model refuses to instantiate.

Together, these make the veto binding impossible to bypass.

## Provider Architecture

### AgentProvider Interface

```python
class AgentProvider(ABC):
    def is_configured() -> bool
    def generate(
        role: str,
        system_prompt: str,
        payload: Dict,
        schema: Type[BaseModel]
    ) -> BaseModel  # Raises ProviderNotConfiguredError, ProviderResponseError, ProviderError
```

All providers are drop-in implementations. Exceptions:

- **ProviderNotConfiguredError:** User manually selected a provider, but required env vars are unset.
  Message names the missing var (e.g., "ANTHROPIC_API_KEY not set"). Only raised in manual mode.
- **ProviderResponseError:** Provider returned invalid JSON or output that fails schema validation.
  HTTP 502.
- **ProviderError:** Upstream failure (rate limit, timeout, model unavailable). HTTP 503.

### The Five Providers

#### MOCK (Default, Offline)

Deterministic, free, keyless, always available. Used in all tests.

**Cost profile:** Zero.

**Env vars:** None required.

**Configuration:** No keys needed; always returns `is_configured() = true`.

**Model:** Hardcoded deterministic rules per role:

- **Technical Analyst:** view = BULLISH if total_return > 0 else BEARISH; confidence = clamp(sharpe, 0, 1)
- **Quant Researcher:** quality = STRONG if profit_factor >= 1.5 and num_trades >= 30, ACCEPTABLE if >= 1.2, else WEAK
- **Bull:** case_strength = win_rate
- **Bear:** case_strength = 1 - win_rate
- **Risk Narrator:** restates the risk verdict verbatim (no interpretation)
- **CIO raw:** PAPER_TRADE if total_return > 0, WATCHLIST if == 0, NO_TRADE if < 0 — **deliberately ignores risk approval** so the veto override is exercised and testable

**Failure behavior:** Never fails; mock is always available.

#### ANTHROPIC (Optional, Premium)

Official `anthropic` Python SDK, via `messages.parse()` with schema validation.

**Cost profile:** Per-token billing; Claude Opus ~8x more expensive than Haiku (varies by region/account).

**Env vars:**
- `ANTHROPIC_API_KEY` — required; raises `ProviderNotConfiguredError` if unset.
- `ANTHROPIC_MODEL` — optional, default `claude-opus-4-8`.

**Configuration:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_MODEL="claude-opus-4-8"  # or "claude-3-5-sonnet", "claude-3-haiku", etc.
```

**Failure behavior:** If provider fails (rate limit, quota, model unavailable), raises `ProviderError` (HTTP 503).

#### GEMINI (Optional, Free-Tier Cloud)

Google Gemini via REST + `httpx`, JSON response mode. Free tier available with modest rate limits.

**Cost profile:** Free tier (daily limits); paid tier variable.

**Env vars:**
- `GEMINI_API_KEY` — required; raises `ProviderNotConfiguredError` if unset.
- `GEMINI_MODEL` — optional, default `gemini-2.0-flash`.

**Configuration:**
```bash
export GEMINI_API_KEY="AIzaSy..."
export GEMINI_MODEL="gemini-2.0-flash"  # or "gemini-1.5-flash", etc.
```

**Failure behavior:** If provider fails (rate limit, key invalid, model unavailable), raises `ProviderError` (HTTP 503).

#### OPENROUTER (Optional, Flexible Cloud with Free Models)

Flexible routing via OpenRouter (REST + `httpx`) with support for free-model endpoints (e.g., Llama, Mistral).

**Cost profile:** Per-token (varies by model); free-model endpoints available via `:free` suffix (rate limits apply; availability depends on account/provider).

**Env vars:**
- `OPENROUTER_API_KEY` — required; raises `ProviderNotConfiguredError` if unset.
- `OPENROUTER_MODEL` — optional, default `meta-llama/llama-3.3-70b-instruct:free` (note `:free` suffix; omit for paid).

**Configuration:**
```bash
export OPENROUTER_API_KEY="sk-or-..."
export OPENROUTER_MODEL="meta-llama/llama-3.3-70b-instruct:free"
```

**Failure behavior:** If provider fails (rate limit, key invalid, model unavailable, or free quota exhausted), raises `ProviderError` (HTTP 503).

#### OLLAMA (Optional, Local)

Local LLM via Ollama REST API. Quality depends on the local model and hardware.

**Cost profile:** Zero (local).

**Env vars:**
- `OLLAMA_BASE_URL` — optional, default `http://localhost:11434`.
- `OLLAMA_MODEL` — optional, default `llama3.2`.

**Configuration:**
```bash
# Start Ollama (must be running for is_configured to return true)
ollama pull llama3.2
ollama serve  # or run as a service

# In the app:
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.2"
```

**Availability probe:** `is_configured()` runs a 1.5-second timeout GET to `{OLLAMA_BASE_URL}/api/tags`.
If the probe fails, `is_configured() = false`. Otherwise true.

**Failure behavior:** If provider fails (model not found, timeout, Ollama not running), raises `ProviderError` (HTTP 503).

### Manual vs. Auto Mode

#### Manual Mode (Specific Provider Named)

When `provider` is explicitly specified in the request (e.g., `"provider": "anthropic"`):

- **If configured:** Use it; return response with `requested_provider="anthropic"`, `selected_provider="anthropic"`.
- **If unconfigured:** HTTP 503 with a helpful error message naming the missing env var. **Never falls back.**

Example error:
```json
{
  "detail": "Provider 'anthropic' not configured: ANTHROPIC_API_KEY not set"
}
```

#### Auto Mode (Provider="auto" or env Default)

When `provider` is omitted from the request (uses env default, e.g., `QUANTCOUNCIL_AGENT_PROVIDER`):

Auto picks the first **configured** provider in priority order:

1. **Anthropic** (highest quality if available)
2. **Gemini** (free-tier cloud option)
3. **OpenRouter** (flexible cloud with free models)
4. **Ollama** (local, quality depends on hardware)
5. **Mock** (always available, offline fallback)

Example flow:
- ANTHROPIC_API_KEY is set → use Anthropic, return `selected_provider="anthropic"`.
- ANTHROPIC_API_KEY is unset, GEMINI_API_KEY is set → use Gemini, return `selected_provider="gemini"`.
- All keys unset, Ollama is running → use Ollama, return `selected_provider="ollama"`.
- Nothing configured → use Mock, return `selected_provider="mock"`.

Response always includes both `requested_provider` and `selected_provider` so the client knows
what was requested and what was actually used.

### Zero-Credentials Guarantee

**The default is `QUANTCOUNCIL_AGENT_PROVIDER=mock`.** The system is fully functional with zero
LLM credentials. `ANTHROPIC_API_KEY` (or any cloud provider key) is optional; absence does not
break anything. The app and all 502 tests run with ZERO LLM credentials — the default mock
provider is deterministic and offline.

## API Endpoints

### POST /committee/evaluate

Evaluate a backtest with the AI committee and issue a CIO decision.

**Request:**

```json
{
  "backtest_id": "550e8400-e29b-41d4-a716-446655440000",
  "risk_evaluation_id": "550e8400-e29b-41d4-a716-446655440001",
  "provider": "mock|auto|anthropic|gemini|openrouter|ollama"
}
```

- `backtest_id`: UUID of the persisted backtest run (required).
- `risk_evaluation_id`: UUID of the persisted risk evaluation for this backtest (required).
- `provider`: optional (default env `QUANTCOUNCIL_AGENT_PROVIDER`, default "mock"). Allowed values:
  `mock`, `auto`, `anthropic`, `gemini`, `openrouter`, `ollama`.

**Loading:**

- Loads the backtest from `backtest_runs`; 404 if not found.
- Loads the risk evaluation from `risk_evaluations`; 404 if not found.
- Validates that both `backtest_id` and `risk_evaluation_id` match (400 if mismatch).
- Builds deterministic context (strategy, metrics, risk verdict, trades, symbol, dates).

**Processing:**

- Runs the six agents in order, accumulating outputs in `committee_so_far`.
- Persists each agent output to `agent_decisions` (one row per agent, rows 1–6).
- Applies code-level risk veto (override to NO_TRADE if CIO raw said PAPER_TRADE but risk rejected).
- Builds final `CIODecision` with `approved_by_risk` copied from the risk evaluation.
- Validates final decision against schema (rejects if veto violated).
- Persists final `CIODecision` as row 7.

**Response (200):**

```json
{
  "backtest_id": "550e8400-e29b-41d4-a716-446655440000",
  "risk_evaluation_id": "550e8400-e29b-41d4-a716-446655440001",
  "requested_provider": "auto|mock|anthropic|...",
  "selected_provider": "mock|anthropic|...",
  "technical_analyst": { ... },
  "quant_researcher": { ... },
  "bull_case": { ... },
  "bear_case": { ... },
  "risk_narrator": { ... },
  "cio_raw": { ... },
  "cio": {
    "decision": "PAPER_TRADE|NO_TRADE|WATCHLIST",
    "summary": "...",
    "reason": "...",
    "conditions_to_reconsider": [...],
    "approved_by_risk": true|false,
    "override_warning": null|"CIO raw PAPER_TRADE overridden..."
  },
  "override_warning": null|"...",
  "agent_decision_ids": [
    "550e8400-... (technical_analyst)",
    "550e8400-... (quant_researcher)",
    "550e8400-... (bull)",
    "550e8400-... (bear)",
    "550e8400-... (risk_narrator)",
    "550e8400-... (cio_raw)",
    "550e8400-... (cio final)"
  ]
}
```

**Error responses:**

| Code | Meaning | Detail |
|---|---|---|
| `400` | Backtest and risk evaluation mismatch, or invalid UUID | Message names the mismatch |
| `404` | Backtest or risk evaluation not found | Message names which id is missing |
| `502` | Provider returned invalid output (malformed JSON, schema validation failed) | Message includes raw response (truncated) |
| `503` | Provider not configured (manual mode) or DB down | Message names the missing env var (manual mode) or error (DB) |

### GET /committee/backtests/{backtest_id}

Retrieve all persisted committee decisions for a backtest, newest first.

**Response (200):**

```json
{
  "backtest_id": "550e8400-e29b-41d4-a716-446655440000",
  "count": 1,
  "decisions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "agent_role": "cio",
      "model": "mock:final",
      "output": { "decision": "PAPER_TRADE", ... },
      "created_at": "2026-07-08T10:30:00Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "agent_role": "cio_raw",
      "model": "mock",
      "output": { "decision": "PAPER_TRADE", ... },
      "created_at": "2026-07-08T10:30:00Z"
    },
    ...
  ]
}
```

**Error responses:**

| Code | Meaning |
|---|---|
| `404` | Backtest not found, or no committee decisions for this backtest |
| `503` | Database unreachable |

## Persistence

### Agent Decisions Table Schema

`agent_decisions` table holds all agent outputs (7 rows per complete committee run):

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `backtest_id` | UUID | FK to `backtest_runs` |
| `risk_evaluation_id` | UUID | FK to `risk_evaluations` |
| `agent_role` | String | technical_analyst, quant_researcher, bull, bear, risk_narrator, cio_raw, cio |
| `model` | String | Provider and role; e.g., "mock", "anthropic", "mock:final" (final CIO marked with ":final") |
| `input` | JSON | Exact payload the agent received (incl. `committee_so_far` for roles 2–6) |
| `output` | JSON | Validated agent output (Pydantic dump) |
| `created_at` | DateTime | Timestamp |

### 7-Row Scheme

Per `POST /committee/evaluate` call:

1. **Row 1:** technical_analyst (input = strategy + metrics + risk verdict)
2. **Row 2:** quant_researcher (input = row 1 output + prior context)
3. **Row 3:** bull (input = row 2 output + prior context)
4. **Row 4:** bear (input = row 3 output + prior context)
5. **Row 5:** risk_narrator (input = row 4 output + prior context)
6. **Row 6:** cio_raw (input = row 5 output + prior context; **no approved_by_risk field**)
7. **Row 7:** cio (final, with approved_by_risk + override_warning; model marked `:final`)

### Audit References

The response includes `agent_decision_ids`: a 7-element list of row IDs in order. Clients can
walk backwards through the chain via the `input` field (which includes `committee_so_far`)
to reconstruct the full debate.

Example: `agent_decision_ids[6]` (final CIO) references `agent_decision_ids[0:6]` in its
`input.audit_refs` or `committee_so_far` field, enabling full traceability.

## Typical Workflow (with curl)

```bash
# 1. Run and persist a backtest
curl -X POST http://localhost:8000/backtests/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": {...full strategy JSON...},
    "symbol": "RELIANCE",
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    "persist": true
  }'
# Returns: {"backtest_id": "550e8400-...", ...}

# 2. Evaluate the backtest's risk
curl -X POST http://localhost:8000/risk/evaluate \
  -H "Content-Type: application/json" \
  -d '{"backtest_id": "550e8400-..."}'
# Returns: {"risk_evaluation_id": "550e8400-...", "approved": true, "decision": "APPROVED", ...}

# 3. Run the committee (uses default provider, mock by default)
curl -X POST http://localhost:8000/committee/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "backtest_id": "550e8400-...",
    "risk_evaluation_id": "550e8400-..."
  }'
# Returns: {"backtest_id": "...", "risk_evaluation_id": "...", "technical_analyst": {...}, ..., "cio": {...}}

# 4. Optionally, re-run with Anthropic (after setting ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY="sk-ant-..."
curl -X POST http://localhost:8000/committee/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "backtest_id": "550e8400-...",
    "risk_evaluation_id": "550e8400-...",
    "provider": "anthropic"
  }'

# 5. If cio.decision == PAPER_TRADE, the human may manually create a paper order
#    via POST /paper/orders (the committee never does this; the veto is enforced again there)
curl -X POST http://localhost:8000/paper/orders \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": "550e8400-...",
    "side": "BUY",
    "symbol": "RELIANCE",
    "quantity": 10,
    "price_reference": 2850.0,
    "thesis": "Committee approved",
    "stop_loss_price": 2700.0,
    "backtest_id": "550e8400-...",
    "risk_evaluation_id": "550e8400-..."
  }'
# Returns: filled order (or 403 if risk not approved — veto enforced again here)

# 6. Retrieve committee history for a backtest
curl http://localhost:8000/committee/backtests/550e8400-...
# Returns: all agent decisions, newest first
```

## Limitations (Phase 6)

1. **Single-shot agent responses; no retry on malformed output.** If an LLM provider returns
   invalid JSON or fails schema validation, the error is 502 without retry. Rationale: Phase 6
   plumbing verification; resilience logic arrives in Phase 7+.

2. **No committee-triggered paper orders.** The committee decides; the human creates the order.
   `POST /committee/evaluate` never calls `POST /paper/orders`. The veto is enforced at order
   creation time (the evaluation is loaded again). Rationale: keeps Phase 6 scope tight, and
   a human review between decision and execution adds oversight.

3. **Free-model limits on OpenRouter and Gemini depend on account/provider.** Free-tier
   rate limits may throttle or pause the committee mid-run. Plan accordingly or use paid tiers.

4. **Ollama quality depends on local hardware.** Smaller models (e.g., llama2) run on modest
   machines but produce simpler outputs. Larger models (70B+) require significant GPU memory.
   Start with a free model and monitor quality before relying on Ollama in production.

5. **No committee configuration per strategy type.** All agents use the same provider and model
   (per call). Dynamic role-specific models (e.g., bear on Opus, analyst on Haiku) deferred.

6. **Context size not tuned for long trade lists.** If a backtest has 100+ trades, the full
   trade summary may exceed a provider's token limits. Phase 7 may add trade-list summarization.

## Testing

From the repo root:

```
pytest
```

Phase 6 test suites:

- `packages/agents/tests/` — 85 tests covering agent schemas, mock provider determinism,
  veto binding (code override + schema validator), persistence, error cases.
- `apps/api/tests/test_committee.py` — 14 tests covering API endpoints, backtest/risk mismatch
  detection, provider selection (manual/auto), integration.

All tests run offline with ZERO LLM credentials (mock provider). Cloud providers are never
called (transports monkeypatched in fixtures). Total: 502 tests passing repo-wide.
