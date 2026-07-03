"""Structured fact store — the EXACT-answer fast lane (hybrid retrieval, D-65).

For the 6 covered schemes and a fixed set of fact types, we answer from an
exact (scheme × data_type → value) table instead of guessing via embedding
similarity. This makes scheme-fact answers verbatim-accurate and impossible to
mismatch to a similar-but-wrong chunk (edge RET-10), with the citation + date
taken straight from the fact's own record.

Two layers, merged at load:
  1. **Seeded regulatory facts** (derived in code from ``schemes.json``): lock-in
     per scheme + the ELSS Section-80C benefit. These are fixed by SEBI / the
     Income Tax Act, so they are authoritative and never overwritten by a scrape.
  2. **Scraped facts** (``data/facts.json``, written by ingestion): market values
     such as expense ratio, NAV, AUM, exit load. Absent until an ingest run.

Anything not in the table falls back to the semantic retriever (see main.py).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend import corpus

# Footer date label for facts fixed by regulation (not a scrape date).
REGULATORY_DATE = "fixed by regulation"

# Path to the optional scraped-facts file (written by ingestion/build_facts.py).
FACTS_PATH: Path = corpus.ROOT_DIR / "data" / "facts.json"

# Classifier ``data_type_hint`` → fact-store key synonyms (D-58 hints are
# granular; the fact store uses a few canonical keys).
_DATA_TYPE_ALIASES: dict[str, str] = {
    "tax": "tax_benefit",
    "sip": "sip_details",
}

# Acronyms to keep upper-cased in rendered sentences.
_ACRONYMS = {"aum": "AUM", "nav": "NAV", "sip": "SIP", "ter": "TER", "elss": "ELSS"}


@dataclass(frozen=True)
class FactRecord:
    """One exact fact: the value plus its own citation + freshness."""

    scheme_name: str
    data_type: str
    value: str
    source_url: str
    scrape_date: str
    display_name: str = ""


def _elss_source_url() -> str:
    """Citation for the ELSS Section-80C tax benefit (AMC official page)."""
    for s in corpus.SOURCES:
        if s.get("id") == "amc_elss_official":
            return s["url"]
    # Fallback: the ELSS Groww scheme page (still in the allow-list).
    for scheme in corpus.SCHEMES:
        if scheme.get("has_lock_in"):
            return scheme["url"]
    return corpus.EDUCATIONAL_URL


def _build_seeded() -> dict[str, dict[str, FactRecord]]:
    """Derive regulatory facts from the scheme registry (single source of truth)."""
    table: dict[str, dict[str, FactRecord]] = {}
    for scheme in corpus.SCHEMES:
        name = scheme["canonical_name"]
        display = scheme.get("short_name") or name
        url = scheme["url"]
        per_scheme: dict[str, FactRecord] = {}

        # Lock-in (every scheme has a definite answer).
        if scheme.get("has_lock_in"):
            years = scheme.get("lock_in_years", 3)
            value = f"{years} years"
        else:
            value = "None"
        per_scheme["lock_in"] = FactRecord(
            scheme_name=name,
            data_type="lock_in",
            value=value,
            source_url=url,
            scrape_date=REGULATORY_DATE,
            display_name=display,
        )

        # ELSS-only: Section 80C tax benefit.
        if scheme.get("has_lock_in"):
            per_scheme["tax_benefit"] = FactRecord(
                scheme_name=name,
                data_type="tax_benefit",
                value="up to ₹1.5 lakh under Section 80C",
                source_url=_elss_source_url(),
                scrape_date=REGULATORY_DATE,
                display_name=display,
            )

        table[name] = per_scheme
    return table


def _load_scraped() -> dict[str, dict[str, FactRecord]]:
    """Load scraped facts from data/facts.json if present (best-effort)."""
    if not FACTS_PATH.exists():
        return {}
    try:
        doc = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    table: dict[str, dict[str, FactRecord]] = {}
    for scheme_name, facts in (doc.get("facts") or {}).items():
        display = _display_for(scheme_name)
        per_scheme: dict[str, FactRecord] = {}
        for data_type, rec in facts.items():
            url = rec.get("source_url", "")
            # Only trust a citation that is in the corpus allow-list (INV-6).
            if not corpus.is_allowed_url(url):
                continue
            value = str(rec.get("value", "")).strip()
            if not value:
                continue
            per_scheme[data_type] = FactRecord(
                scheme_name=scheme_name,
                data_type=data_type,
                value=value,
                source_url=url,
                scrape_date=str(rec.get("scrape_date", "")),
                display_name=display,
            )
        if per_scheme:
            table[scheme_name] = per_scheme
    return table


def _display_for(canonical: str) -> str:
    for scheme in corpus.SCHEMES:
        if scheme["canonical_name"] == canonical:
            return scheme.get("short_name") or canonical
    return canonical


def _merge(
    seeded: dict[str, dict[str, FactRecord]],
    scraped: dict[str, dict[str, FactRecord]],
) -> dict[str, dict[str, FactRecord]]:
    """Merge layers. Scraped fills extra fields; seeded regulatory facts win."""
    merged: dict[str, dict[str, FactRecord]] = {}
    schemes = set(seeded) | set(scraped)
    for name in schemes:
        per_scheme = dict(scraped.get(name, {}))
        per_scheme.update(seeded.get(name, {}))  # seeded overrides scraped
        merged[name] = per_scheme
    return merged


# ── Load once at import (like corpus) ─────────────────────────────────────
_FACTS: dict[str, dict[str, FactRecord]] = _merge(_build_seeded(), _load_scraped())


def lookup(scheme_name: str | None, data_type: str | None) -> FactRecord | None:
    """Return the exact fact for (scheme, data_type), or None.

    ``data_type`` accepts the classifier's granular hint; a small alias map
    bridges it to the fact-store keys.
    """
    if not scheme_name or not data_type:
        return None
    key = _DATA_TYPE_ALIASES.get(data_type, data_type)
    return _FACTS.get(scheme_name, {}).get(key)


def render(fact: FactRecord) -> str:
    """Render an exact fact as a single, plain-language sentence (no LLM)."""
    name = fact.display_name or fact.scheme_name
    if fact.data_type == "lock_in":
        if fact.value.strip().lower() in {"none", "no", "nil", "0"}:
            return f"{name} has no lock-in period."
        return f"The lock-in period of {name} is {fact.value}."
    if fact.data_type == "tax_benefit":
        return f"Investing in {name} qualifies for a tax deduction of {fact.value}."
    if fact.data_type == "sip_details":
        return f"The minimum SIP for {name} is {fact.value}."
    label = " ".join(_ACRONYMS.get(w, w) for w in fact.data_type.split("_"))
    return f"The {label} of {name} is {fact.value}."


def has_fact(scheme_name: str | None, data_type: str | None) -> bool:
    return lookup(scheme_name, data_type) is not None
