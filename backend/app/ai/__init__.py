"""AI integration package (Phase 2).

The provider registry discovers credentials from the environment only. When no
provider is configured the platform falls back to the deterministic rule-based
engine in :mod:`app.ai.engine`, so every feature works fully offline.
"""
