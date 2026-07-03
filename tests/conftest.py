"""Shared test setup.

Ensures a dummy GROQ_API_KEY is present so importing backend.config / backend.main
succeeds in any environment (tests never call Groq — they inject/monkeypatch).
"""

from __future__ import annotations

import os

# Set a placeholder key before any backend.config import if one isn't provided.
os.environ.setdefault("GROQ_API_KEY", "test-key-not-real")
os.environ.setdefault("REQUIRE_SECRETS", "1")
