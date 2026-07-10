# QuantCouncil LLM Providers (Phase 6)

Comprehensive reference for the provider abstraction, configuration, and selection logic.
All providers are drop-in implementations of the `AgentProvider` interface in `packages/agents`.

## Philosophy: Zero Credentials, Any Provider

The system works with **zero LLM credentials**. The default provider is MOCK (deterministic,
offline). Premium LLM providers (Anthropic, Gemini, OpenRouter, Ollama) are optional; configure
them with env vars and the system automatically uses them when available. The system never
requires an LLM API key to function.

## Provider Abstraction

All providers implement this interface (`packages/agents/agents/providers/base.py`):

```python
class AgentProvider(ABC):
    """
    Agent provider contract.
    """
    
    def is_configured(self) -> bool:
        """
        Return True if this provider is ready to generate outputs.
        False if required env vars are unset or services are unavailable.
        """
    
    def generate(
        self,
        role: str,
        system_prompt: str,
        payload: Dict,
        schema: Type[BaseModel]
    ) -> BaseModel:
        """
        Generate an agent output, validate against schema, return Pydantic instance.
        
        Raises:
        - ProviderNotConfiguredError: manual mode, provider selected but not configured
        - ProviderResponseError: invalid JSON or schema validation failed (HTTP 502)
        - ProviderError: upstream failure — rate limit, timeout, model unavailable (HTTP 503)
        """
```

Exception hierarchy:

```
ProviderError (base)
├── ProviderNotConfiguredError (manual mode only; includes missing env var name)
├── ProviderResponseError (malformed output; includes raw response truncated)
└── (base class also used for timeouts, rate limits, service unavailable)
```

## Providers Summary Table

| Provider | Cost | Setup | Availability | Quality | Best For |
|---|---|---|---|---|---|
| **MOCK** | Free | None | Always (offline) | Deterministic, simple | Testing, default, offline |
| **Anthropic** | Per-token ($$) | API key + optional model name | When key set | Premium (Claude Opus/Sonnet/Haiku) | Production, highest quality |
| **Gemini** | Free tier + paid | API key + optional model name | When key set | Good (Gemini 2.0 Flash) | Free cloud option |
| **OpenRouter** | Per-token (variable) | API key + optional model name | When key set | Variable (Llama, Mistral, etc.) | Flexible, free-model support |
| **Ollama** | Free (local) | Port 11434 + model downloaded | When Ollama running | Depends on local model/GPU | Offline, privacy, local control |

## The Five Providers

### 1. MOCK (Default, Deterministic, Offline)

**What it is:** Hardcoded, deterministic response logic. No HTTP, no API key, no LLM involved.
Every call produces the same output given identical inputs.

**Cost profile:** Zero.

**Env vars:** None required.

**Configuration:** Always available. No setup needed.

**Default model behavior:** Hardcoded rules per agent role (see [ai-committee.md](ai-committee.md)).
Examples:
- **Technical Analyst:** view = BULLISH if total_return > 0 else BEARISH
- **CIO raw:** decision = PAPER_TRADE if total_return > 0, WATCHLIST if == 0, NO_TRADE if < 0

**Determinism guarantee:** Identical metrics produce identical outputs every time, making mock
ideal for testing, development, and local-first workflows.

**Failure behavior:** Never fails. `is_configured()` always returns `true`.

### 2. ANTHROPIC (Premium, Official SDK)

**What it is:** Official `anthropic` Python SDK with `messages.parse()` for structured outputs.
Real LLM reasoning via Claude Opus (default), Sonnet, Haiku, or other Claude models.

**Cost profile:** Per-token billing. Opus (~8x Haiku cost), Sonnet (~3x Haiku), Haiku (~1x baseline).
Prices vary by region and account tier. Typical committee run: 5–20 API tokens depending on
complexity.

**Env vars:**

- `ANTHROPIC_API_KEY` — required. Format: `sk-ant-...`. Obtain from https://console.anthropic.com.
- `ANTHROPIC_MODEL` — optional, default `claude-opus-4-8`. Examples: `claude-3-5-sonnet-20241022`,
  `claude-3-haiku-20240307`.

**Configuration:**

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
export ANTHROPIC_MODEL="claude-opus-4-8"  # or any Claude model
```

**Setup steps:**

1. Create an account at https://console.anthropic.com.
2. Generate an API key.
3. Set `ANTHROPIC_API_KEY` and optionally `ANTHROPIC_MODEL` in your environment.

**Model selection:**
- **Opus:** Best quality; slower; most expensive. Recommended for production.
- **Sonnet:** Good quality; moderate speed; balanced cost. Recommended for cost-conscious production.
- **Haiku:** Fast; lowest cost; decent quality for simple tasks. Good for high-volume trials.

**Failure behavior:**

- If `ANTHROPIC_API_KEY` is unset and the provider is explicitly requested (manual mode),
  raise `ProviderNotConfiguredError` with message: `"ANTHROPIC_API_KEY not set"`.
- If the API returns a rate-limit or quota error, raise `ProviderError` (HTTP 503).
- If output fails schema validation, raise `ProviderResponseError` (HTTP 502).

### 3. GEMINI (Free-Tier Cloud, REST)

**What it is:** Google Gemini via REST API + `httpx`. JSON response mode with schema validation.
Free tier available with modest rate limits; paid tier available for higher volume.

**Cost profile:** Free tier (daily limits; varies by region), or paid-per-token (variable cost).

**Env vars:**

- `GEMINI_API_KEY` — required. Format: Google API key (alphanumeric string). Obtain from
  https://ai.google.dev/gemini-api.
- `GEMINI_MODEL` — optional, default `gemini-2.0-flash`. Examples: `gemini-1.5-flash`,
  `gemini-1.5-pro`.

**Configuration:**

```bash
export GEMINI_API_KEY="AIzaSy..."
export GEMINI_MODEL="gemini-2.0-flash"
```

**Setup steps:**

1. Go to https://ai.google.dev/gemini-api.
2. Sign in with a Google account.
3. Create an API key (no credit card required for free tier).
4. Set `GEMINI_API_KEY` and optionally `GEMINI_MODEL` in your environment.

**Model selection:**
- **Gemini 2.0 Flash:** Default; fastest; good quality.
- **Gemini 1.5 Flash:** Older, slightly slower; good quality.
- **Gemini 1.5 Pro:** Slower; higher quality; uses more quota.

**Rate limits (free tier):**
- ~600 requests per minute (varies).
- Contact Google if you need higher limits (upgraded account).

**Failure behavior:**

- If `GEMINI_API_KEY` is unset and the provider is explicitly requested (manual mode),
  raise `ProviderNotConfiguredError` with message: `"GEMINI_API_KEY not set"`.
- If the API returns a rate-limit or quota error, raise `ProviderError` (HTTP 503).
- If output fails schema validation, raise `ProviderResponseError` (HTTP 502).

### 4. OPENROUTER (Flexible Cloud, Multiple Models)

**What it is:** OpenRouter REST API (httpx) routing to multiple LLM providers (Anthropic, Together,
Mistral, Llama via Together, etc.). Free-model endpoints available (e.g., `llama-3.3-70b:free`).

**Cost profile:** Per-token (varies by model). Free-model endpoints available via `:free` suffix,
subject to rate limits.

**Env vars:**

- `OPENROUTER_API_KEY` — required. Format: `sk-or-...`. Obtain from https://openrouter.ai.
- `OPENROUTER_MODEL` — optional, default `meta-llama/llama-3.3-70b-instruct:free`. Examples:
  - `anthropic/claude-3-opus` (paid, via OpenRouter)
  - `meta-llama/llama-3.3-70b-instruct:free` (free tier, rate-limited)
  - `mistralai/mistral-7b:free`

**Configuration:**

```bash
export OPENROUTER_API_KEY="sk-or-your-key-here"
export OPENROUTER_MODEL="meta-llama/llama-3.3-70b-instruct:free"
```

**Setup steps:**

1. Go to https://openrouter.ai.
2. Sign up (free account).
3. Generate an API key.
4. Set `OPENROUTER_API_KEY` and optionally `OPENROUTER_MODEL` in your environment.
5. Note: Free-model `:free` endpoints require a free or paid account and are subject to
   availability and rate limits.

**Free-model availability:**
- `:free` models depend on the provider's (Together, Replicate, etc.) capacity.
- If a `:free` model hits rate limits, you may need a paid account or a different model.
- Check https://openrouter.ai/models for current availability.

**Paid-model availability:**
- All major models (Claude, Gemini, Mistral, Llama paid) available via OpenRouter.
- Pricing varies; generally comparable to or slightly higher than direct API calls.

**Failure behavior:**

- If `OPENROUTER_API_KEY` is unset and the provider is explicitly requested (manual mode),
  raise `ProviderNotConfiguredError` with message: `"OPENROUTER_API_KEY not set"`.
- If the API returns a rate-limit or quota error, raise `ProviderError` (HTTP 503).
- If output fails schema validation, raise `ProviderResponseError` (HTTP 502).

### 5. OLLAMA (Local, Privacy-First)

**What it is:** Local Ollama REST API (httpx) to a locally running LLM. Runs entirely on your
machine; no cloud provider; offline by nature.

**Cost profile:** Zero (local), but requires GPU/CPU with sufficient memory.

**Env vars:**

- `OLLAMA_BASE_URL` — optional, default `http://localhost:11434`.
- `OLLAMA_MODEL` — optional, default `llama3.2`.

**Configuration:**

```bash
# Start Ollama (one-time setup)
ollama pull llama3.2
# Then run Ollama as a background service or process:
ollama serve

# In your environment (or .env):
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.2"
```

**Setup steps:**

1. Download and install Ollama from https://ollama.ai.
2. Pull a model: `ollama pull llama3.2` (or another model).
3. Start Ollama: `ollama serve` (or configure as a system service).
4. Verify it's running: `curl http://localhost:11434/api/tags` (should list your models).
5. Set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` (optional if using defaults).

**Model selection:**
- **llama3.2** (default, 8B): Fast, modest quality, runs on 8GB GPU.
- **llama2** (7B): Older, slightly worse quality, runs on 8GB GPU.
- **mistral** (7B): Good quality, faster than Llama.
- **llama3-70b** (70B): High quality, requires 40GB+ VRAM or CPU patience.

**Availability probe:** `is_configured()` runs a GET request to `{OLLAMA_BASE_URL}/api/tags`
with a 1.5-second timeout. If it succeeds, `is_configured() = true`; otherwise `false`.
This ensures the system knows Ollama is not running before attempting a generate call.

**Failure behavior:**

- If Ollama is not running or the probe times out, `is_configured() = false`. Auto mode will
  skip Ollama and try the next provider.
- If explicitly requested (manual mode) but not running, raise `ProviderError` (HTTP 503)
  with message: `"Ollama not running at http://localhost:11434"` (or configured URL).
- If output fails schema validation, raise `ProviderResponseError` (HTTP 502).

## Manual vs. Auto Mode

### Manual Mode (Explicit Provider)

When a provider is explicitly named in a request (e.g., `"provider": "anthropic"`):

**If configured:** Use it. Return response with `requested_provider="anthropic"`, `selected_provider="anthropic"`.

**If unconfigured:** Raise `ProviderNotConfiguredError` and return HTTP 503 with error detail naming
the missing env var. **Never falls back to another provider.**

Example error:
```json
{
  "detail": "Provider 'anthropic' not configured: ANTHROPIC_API_KEY not set"
}
```

### Auto Mode (No Provider Specified or provider="auto")

When `provider` is omitted from the request (uses env default `QUANTCOUNCIL_AGENT_PROVIDER`),
the system auto-selects the first configured provider in priority order:

1. **Anthropic** (highest quality if available)
2. **Gemini** (free-tier cloud option)
3. **OpenRouter** (flexible cloud with free models)
4. **Ollama** (local, quality depends on hardware)
5. **Mock** (always available, offline fallback)

**Selection flow:**

```
if ANTHROPIC_API_KEY set:
    use Anthropic
else if GEMINI_API_KEY set:
    use Gemini
else if OPENROUTER_API_KEY set:
    use OpenRouter
else if Ollama is_configured():
    use Ollama
else:
    use Mock (always available)
```

**Response:** Always includes both `requested_provider` and `selected_provider`:

```json
{
  "requested_provider": "auto",
  "selected_provider": "mock",
  ...
}
```

Client knows what was requested and what was actually used.

## Environment Variable Reference

| Variable | Allowed Values | Default | Example | Required |
|---|---|---|---|---|
| `QUANTCOUNCIL_AGENT_PROVIDER` | `mock`, `auto`, `anthropic`, `gemini`, `openrouter`, `ollama` | `mock` | `export QUANTCOUNCIL_AGENT_PROVIDER=mock` | No |
| `ANTHROPIC_API_KEY` | String (sk-ant-...) | Unset | `sk-ant-...` | Only if using Anthropic |
| `ANTHROPIC_MODEL` | Claude model name | `claude-opus-4-8` | `claude-3-5-sonnet-20241022` | No |
| `GEMINI_API_KEY` | String (alphanumeric) | Unset | `AIzaSy...` | Only if using Gemini |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.0-flash` | `gemini-1.5-pro` | No |
| `OPENROUTER_API_KEY` | String (sk-or-...) | Unset | `sk-or-...` | Only if using OpenRouter |
| `OPENROUTER_MODEL` | OpenRouter model id | `meta-llama/llama-3.3-70b-instruct:free` | `anthropic/claude-3-opus` | No |
| `OLLAMA_BASE_URL` | HTTP URL | `http://localhost:11434` | `http://192.168.1.10:11434` | No |
| `OLLAMA_MODEL` | Ollama model name | `llama3.2` | `mistral` | No |

## Zero-Credentials Guarantee

**The default configuration requires zero LLM credentials.**

- Default `QUANTCOUNCIL_AGENT_PROVIDER=mock` (no keys needed).
- The mock provider is fully functional, deterministic, and offline.
- All 502 tests pass with zero credentials.
- LLM API keys (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.) are optional.

The system works out of the box on any machine without API keys. Configure optional providers
when you want premium quality.

## Configuration Examples

### Scenario 1: Default (Offline, No Keys)

```bash
# No env vars needed
# Default: QUANTCOUNCIL_AGENT_PROVIDER=mock (auto)
python -m pytest  # All tests pass
uvicorn app.main:app  # API runs
curl -X POST http://localhost:8000/committee/evaluate ...
# Returns mock outputs (deterministic, instant, no API calls)
```

### Scenario 2: Optional Anthropic (Best Quality)

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
export ANTHROPIC_MODEL="claude-opus-4-8"
# QUANTCOUNCIL_AGENT_PROVIDER defaults to "mock", but auto mode selects Anthropic if key is set
curl -X POST http://localhost:8000/committee/evaluate \
  -d '{"backtest_id": "...", "risk_evaluation_id": "...", "provider": "auto"}'
# OR explicitly request Anthropic:
curl -X POST http://localhost:8000/committee/evaluate \
  -d '{"backtest_id": "...", "risk_evaluation_id": "...", "provider": "anthropic"}'
# Returns high-quality Claude outputs
```

### Scenario 3: Free Gemini Cloud

```bash
export GEMINI_API_KEY="AIzaSy..."
# No Anthropic key set, so auto mode selects Gemini
curl -X POST http://localhost:8000/committee/evaluate \
  -d '{"backtest_id": "...", "risk_evaluation_id": "...", "provider": "auto"}'
# Returns Gemini outputs (free tier, rate limits apply)
```

### Scenario 4: Local Ollama (Private)

```bash
# Start Ollama in another terminal:
ollama serve

# In your environment:
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.2"

# No cloud keys set, Ollama is running, so auto mode selects it
curl -X POST http://localhost:8000/committee/evaluate \
  -d '{"backtest_id": "...", "risk_evaluation_id": "...", "provider": "auto"}'
# Returns Ollama outputs (local, private, no API calls outside your machine)
```

### Scenario 5: Multiple Keys (Auto Picks Best)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="AIzaSy..."
export OPENROUTER_API_KEY="sk-or-..."
export OLLAMA_BASE_URL="http://localhost:11434"

# QUANTCOUNCIL_AGENT_PROVIDER=mock (default)
# But "provider": "auto" (or omitted) picks Anthropic (highest priority)
curl -X POST http://localhost:8000/committee/evaluate \
  -d '{"backtest_id": "...", "risk_evaluation_id": "..."}'
# Returns response with selected_provider="anthropic"
```

## Rate Limits and Quotas

| Provider | Limit | Note |
|---|---|---|
| **Anthropic** | Rate limits per account; typically ≥10 RPM (standard), higher on higher tiers | Check console; may request higher limits |
| **Gemini** | Free tier ≤600 RPM; paid tiers higher | Varies by region; free tier requires no card |
| **OpenRouter** | Varies by upstream provider; typical ≥1000 RPM | Check openrouter.ai/models for details; free models more restrictive |
| **Ollama** | Local; no external limits | Limited only by CPU/GPU; local rate depends on model size |
| **Mock** | No limit (offline) | Instant, no external service |

For production, use paid tiers (Anthropic Standard+, Gemini paid, OpenRouter paid) to avoid
rate limits.

## Troubleshooting

### Provider not responding (HTTP 503)

1. **Manual mode:** Check that the required env var is set. Error message names it.
   ```bash
   # If using Anthropic manually:
   curl -X POST http://localhost:8000/committee/evaluate \
     -d '{"provider": "anthropic", ...}'
   # If ANTHROPIC_API_KEY is unset, you get: {"detail": "Provider 'anthropic' not configured: ANTHROPIC_API_KEY not set"}
   ```

2. **Auto mode:** Check the selected provider; logs show which one was picked.
   ```bash
   # Set all keys to use auto:
   export ANTHROPIC_API_KEY="..."
   export GEMINI_API_KEY="..."
   export OLLAMA_BASE_URL="http://localhost:11434"
   # Auto picks Anthropic first (highest priority)
   ```

### Rate limit (HTTP 503)

1. Switch to a different provider (if multiple are configured).
   ```bash
   curl -X POST http://localhost:8000/committee/evaluate \
     -d '{"provider": "gemini", ...}'
   ```

2. Use auto mode; it may pick another provider on next call (if available).

3. Upgrade to a paid tier or increase your rate limit with the provider.

### Invalid schema (HTTP 502)

1. Check provider's output format. This is a provider issue (malformed JSON or unexpected field).
2. File an issue with details (truncated response included in error message).
3. Retry (single-shot, no automatic retry in Phase 6).

### Ollama not running

1. Start Ollama:
   ```bash
   ollama serve
   ```

2. Verify:
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. Pull a model if needed:
   ```bash
   ollama pull llama3.2
   ```
