"""Phase 0 smoke tests for configuration loading.

Covers evals E-0.2 (imports resolve) and E-0.3 (missing key fails fast).
Run with: pytest tests/test_config.py
"""

from __future__ import annotations

import importlib
import sys


def _fresh_import():
    """Import backend.config from a clean module state (order-independent)."""
    sys.modules.pop("backend.config", None)
    return importlib.import_module("backend.config")


def test_config_imports_with_secret(monkeypatch):
    """E-0.2: config builds when GROQ_API_KEY is present."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("REQUIRE_SECRETS", "1")

    config = _fresh_import()
    assert config.settings.groq_api_key == "test-key-not-real"
    assert config.settings.groq_model  # has a default
    assert config.settings.top_k >= 1
    assert 0.0 <= config.settings.score_threshold <= 1.0
    assert config.settings.max_sentences == 3


def test_missing_key_fails_fast(monkeypatch):
    """E-0.3 (Gate): a missing GROQ_API_KEY raises a clear ConfigError at load time."""
    # Stub dotenv so the real .env (which now has a key) is not re-read.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("REQUIRE_SECRETS", "1")

    # A fresh import with no key must raise. We catch RuntimeError because
    # ConfigError subclasses it (a reloaded module defines a *new* ConfigError
    # class object, so catching the original reference would miss it).
    raised = False
    try:
        _fresh_import()
    except RuntimeError as exc:
        raised = True
        assert type(exc).__name__ == "ConfigError"
        assert "GROQ_API_KEY" in str(exc)
    assert raised, "Expected ConfigError when GROQ_API_KEY is missing"


def test_offline_mode_skips_secret(monkeypatch):
    """Ingestion/offline tooling can run without Groq when REQUIRE_SECRETS=0."""
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("REQUIRE_SECRETS", "0")

    config = _fresh_import()
    assert config.settings.groq_api_key == ""
