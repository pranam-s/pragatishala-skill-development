# ADR 0005: AI: provider-agnostic clients with deterministic offline fallback

Status: accepted

## Context

The product's core loop (assess → gap → roadmap) must work offline, on a
machine with no guaranteed network, and with no API keys configured during
development. It must also improve automatically when a key exists. The
LLM vendor landscape changes monthly.

## Decision

- One internal contract, `LLMProvider.complete_json(system, user, schema)`.
- Two client implementations: `OpenAICompatibleProvider` (covers OpenAI, Azure
  gateways, Gemini's OpenAI-compat endpoint, Groq, OpenRouter, Ollama, vLLM
  through `base_url`) and `AnthropicProvider` (Messages API). Response JSON is
  fenced-code tolerant and strictly schema-validated with Pydantic; anything
  unusable raises `AIError`.
- `SkillEngine` always computes the deterministic fallback first, then tries
  the provider; any `AIError` logs a warning and returns the fallback. The
  chosen path is persisted as `engine_used`.
- Provider selection (`PRAGATISHALA_AI_PROVIDER`): `auto` (default) picks the
  first configured provider; explicit selections require their key; keys come
  from the environment only.

## Consequences

- The platform never hard-fails on model outages, malformed output, or missing
  keys; worst case is rule-based quality.
- Tests exercise HTTP paths with mocked transports and the engine contract with
  stub providers; no live API calls in CI.
- Vendor lock-in is limited to the JSON prompt/response shape; swapping vendors
  is a `base_url` + model name change, not a code change.
