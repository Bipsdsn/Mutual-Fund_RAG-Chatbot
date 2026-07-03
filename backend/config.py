"""Centralized configuration.

This is the ONLY module that reads ``os.environ`` (see Docs/conventions.md §3).
Everything else imports the singleton ``settings`` and uses typed values.

Fails fast at import time if a required secret is missing, so misconfiguration
surfaces at startup rather than mid-request (edge case SYS-3, decision D-32).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env once, here, and nowhere else.
load_dotenv()

# Repository root = parent of the `backend/` package directory.
ROOT_DIR: Path = Path(__file__).resolve().parent.parent


class ConfigError(RuntimeError):
    """Raised when configuration is missing or invalid."""


def _get(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and (value is None or value.strip() == ""):
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and set it (see Docs/conventions.md §3)."
        )
    return value if value is not None else ""


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name} must be an integer, got {raw!r}.") from exc


def _get_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name} must be a float, got {raw!r}.") from exc


def _get_list(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Typed, immutable application settings."""

    # --- Groq LLM ---
    groq_api_key: str
    groq_model: str

    # --- Embeddings (must match at ingest & query time; decision D-29) ---
    embedding_model: str

    # --- Vector store ---
    chroma_dir: Path
    chroma_collection: str

    # --- Retrieval tunables ---
    top_k: int
    score_threshold: float

    # --- Output contract ---
    max_sentences: int

    # --- API ---
    allowed_origins: list[str] = field(default_factory=list)
    log_level: str = "INFO"

    # --- Scheduler (in-app periodic re-ingestion; OFF by default) ---
    scheduler_enabled: bool = False
    ingest_interval_hours: int = 24
    ingest_run_on_start: bool = False

    # --- Data files (single source of truth) ---
    sources_path: Path = ROOT_DIR / "data" / "sources.json"
    schemes_path: Path = ROOT_DIR / "data" / "schemes.json"


def _build_settings(*, require_secrets: bool = True) -> Settings:
    chroma_dir = Path(_get("CHROMA_DIR", "./data/chroma"))
    if not chroma_dir.is_absolute():
        chroma_dir = (ROOT_DIR / chroma_dir).resolve()

    return Settings(
        groq_api_key=_get("GROQ_API_KEY", required=require_secrets),
        groq_model=_get("GROQ_MODEL", "llama-3.1-8b-instant"),
        embedding_model=_get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        chroma_dir=chroma_dir,
        chroma_collection=_get("CHROMA_COLLECTION", "mf_faq"),
        top_k=_get_int("TOP_K", 5),
        # Tuned empirically against the built index (D-49): legit queries score
        # ~0.71–0.84, off-topic ~0.50–0.57 with bge-small; 0.65 separates them.
        score_threshold=_get_float("SCORE_THRESHOLD", 0.65),
        max_sentences=_get_int("MAX_SENTENCES", 3),
        allowed_origins=_get_list("ALLOWED_ORIGINS", "http://localhost:5173"),
        log_level=_get("LOG_LEVEL", "INFO"),
        scheduler_enabled=_get_bool("SCHEDULER_ENABLED", False),
        ingest_interval_hours=_get_int("INGEST_INTERVAL_HOURS", 24),
        ingest_run_on_start=_get_bool("INGEST_RUN_ON_START", False),
    )


# Secrets are required when running the serving app, but ingestion/tests may not
# need Groq. Allow opting out via REQUIRE_SECRETS=0 for offline tooling.
_require = os.environ.get("REQUIRE_SECRETS", "1") not in {"0", "false", "False"}
settings: Settings = _build_settings(require_secrets=_require)
