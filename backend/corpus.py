"""Corpus & scheme registry loader — the single source of truth for the
20-URL allow-list and the 6 covered schemes (Docs/decisions.md D-25).

Used by BOTH the ingestion pipeline and the citation validator, so "official
sources only" is enforced in one place.

Note: this module reads only JSON files (never ``os.environ``), so it stays
importable offline without a Groq key — keeping config-reading centralized in
``config.py`` per Docs/conventions.md §3.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Paths derived from this file's location (no env access here).
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
SOURCES_PATH: Path = ROOT_DIR / "data" / "sources.json"
SCHEMES_PATH: Path = ROOT_DIR / "data" / "schemes.json"

# Official domains permitted by the brief (Docs/context.md §7).
OFFICIAL_DOMAINS: frozenset[str] = frozenset(
    {
        "groww.in",
        "www.hdfcfund.com",
        "hdfcfund.com",
        "www.sebi.gov.in",
        "sebi.gov.in",
        "investor.sebi.gov.in",
        "files.hdfcfund.com",  # official HDFC document CDN (SID/KIM/factsheets)
        "www.amfiindia.com",
        "amfiindia.com",
    }
)

EXPECTED_SOURCE_COUNT = 20
VALID_SOURCE_TYPES: frozenset[str] = frozenset(
    {"groww_scheme_page", "amc_official", "sebi", "amfi"}
)
VALID_FETCH_MODES: frozenset[str] = frozenset({"html_static", "html_js", "pdf"})


class CorpusError(RuntimeError):
    """Raised when the corpus configuration is missing or invalid."""


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise CorpusError(f"Corpus file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"Invalid JSON in {path}: {exc}") from exc


def _domain_of(url: str) -> str:
    # Lightweight host extraction without importing urllib for clarity.
    without_scheme = url.split("://", 1)[-1]
    return without_scheme.split("/", 1)[0].lower()


# ── Load data once at import ──────────────────────────────────────────────
SOURCES: list[dict[str, Any]] = _load_json(SOURCES_PATH)
_SCHEMES_DOC: dict[str, Any] = _load_json(SCHEMES_PATH)
SCHEMES: list[dict[str, Any]] = _SCHEMES_DOC.get("schemes", [])

# The citation allow-list: responses MUST cite one of these (Docs/conventions.md §9).
ALLOWED_URLS: frozenset[str] = frozenset(s["url"] for s in SOURCES)

# Canonical educational / scope links used by responders + classifier (must be
# in the allow-list above). Single source of truth so the URLs aren't duplicated.
EDUCATIONAL_URL: str = "https://www.amfiindia.com/investor"
AMC_HOME_URL: str = "https://www.hdfcfund.com/mutual-funds/factsheets"

# Canonical covered scheme names (for scope responses / classifier).
COVERED_SCHEMES: list[str] = [s["canonical_name"] for s in SCHEMES]


# ── Public helpers ────────────────────────────────────────────────────────
def is_allowed_url(url: str) -> bool:
    """True iff ``url`` is one of the 20 corpus URLs (Formatter citation check)."""
    return url in ALLOWED_URLS


def get_source(url: str) -> dict[str, Any] | None:
    """Return the source record for a corpus URL, or None."""
    for s in SOURCES:
        if s["url"] == url:
            return s
    return None


def resolve_scheme(text: str) -> str | None:
    """Resolve free text to a canonical scheme name via aliases (longest-first),
    or None if no covered scheme is mentioned (edge RET-6).
    """
    if not text:
        return None
    haystack = text.lower()

    # Build (alias, canonical) pairs, longest alias first so "hdfc mid cap fund"
    # wins over "mid cap".
    candidates: list[tuple[str, str]] = []
    for scheme in SCHEMES:
        canonical = scheme["canonical_name"]
        names = [canonical, scheme.get("short_name", "")]
        for name in filter(None, names):
            candidates.append((name.lower(), canonical))
        for alias in scheme.get("aliases", []):
            candidates.append((alias.lower(), canonical))

    for alias, canonical in sorted(candidates, key=lambda p: len(p[0]), reverse=True):
        if alias and alias in haystack:
            return canonical
    return None


def validate_corpus() -> list[str]:
    """Return a list of problems with the corpus config (empty = valid).

    Used by Phase-1 evals E-1.1..E-1.4. Does not raise, so tests can report all
    issues at once.
    """
    problems: list[str] = []

    urls = [s.get("url", "") for s in SOURCES]

    if len(SOURCES) != EXPECTED_SOURCE_COUNT:
        problems.append(f"Expected {EXPECTED_SOURCE_COUNT} sources, found {len(SOURCES)}.")

    if len(set(urls)) != len(urls):
        problems.append("Duplicate URLs present in sources.json.")

    for s in SOURCES:
        url = s.get("url", "")
        domain = _domain_of(url)
        if domain not in OFFICIAL_DOMAINS:
            problems.append(f"Non-official domain: {domain} ({url}).")
        if s.get("source_type") not in VALID_SOURCE_TYPES:
            problems.append(f"Invalid source_type for {url}: {s.get('source_type')!r}.")
        if s.get("fetch_mode") not in VALID_FETCH_MODES:
            problems.append(f"Invalid fetch_mode for {url}: {s.get('fetch_mode')!r}.")
        for key in ("id", "url", "source_type", "fetch_mode", "default_data_type", "title"):
            if key not in s:
                problems.append(f"Source {url or s.get('id')} missing key '{key}'.")

    if len(SCHEMES) != 6:
        problems.append(f"Expected 6 schemes, found {len(SCHEMES)}.")

    return problems


def source_type_counts() -> dict[str, int]:
    """Count sources by source_type (eval E-1.4)."""
    counts: dict[str, int] = {}
    for s in SOURCES:
        counts[s["source_type"]] = counts.get(s["source_type"], 0) + 1
    return counts
