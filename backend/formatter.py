"""Response Formatter — the single output-contract gate (Phase 7).

EVERY branch passes through here (conventions §6, data-flow §5.4). It enforces,
deterministically (never trusting the LLM):

  1. ≤ MAX_SENTENCES sentences in the body (trim; SC6 / FMT-1).
  2. Exactly one citation, validated ∈ corpus allow-list (SC3 / FMT-2/3).
  3. A freshness footer ("Last updated from sources: <date>") for factual
     answers + the always-present disclaimer footer on every branch (SC7 / FMT-4).
  4. A final PII-echo scan — if any PII slips into the draft, fall back to the
     NO_SOURCE message rather than ship it (PII-10 / FMT-10).
  5. Empty / out-of-corpus / "I don't know" drafts → NO_SOURCE (FMT-6 / E-7.11/12).

Sentence counting is decimal- and URL-aware: it splits only on sentence
punctuation FOLLOWED BY whitespace, so "0.74%", "1234.56", and
"https://investor.sebi.gov.in/riskometer.html" are never miscounted (edge: the
Phase-7 decimal gotcha).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend import corpus
from backend.guardrails import pii
from backend.models import ResponseType
from backend.rag.generator import NOT_IN_SOURCES

DISCLAIMER = "Facts-only. No investment advice."
FRESHNESS_PREFIX = "Last updated from sources:"

# Split on . ! ? ONLY when followed by whitespace — leaves decimals/URLs intact.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Formatted:
    """Contract-compliant response, ready to map onto QueryResponse."""

    answer: str
    source_url: str | None
    last_updated: str | None
    response_type: ResponseType
    refused: bool


# ── Pure text helpers (offline-testable) ──────────────────────────────────
def split_sentences(text: str) -> list[str]:
    """Split into sentences without breaking on decimals or URLs."""
    text = (text or "").strip()
    if not text:
        return []
    return [s for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]


def trim_sentences(text: str, max_sentences: int) -> str:
    """Keep at most ``max_sentences`` sentences (FMT-1)."""
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return text.strip()
    return " ".join(sentences[:max_sentences]).strip()


def freshness_footer(scrape_date: str | None) -> str | None:
    """The freshness line, or None when there is no scrape_date."""
    if not scrape_date:
        return None
    return f"{FRESHNESS_PREFIX} {scrape_date}"


def _strip_trailing_disclaimer(body: str) -> str:
    b = (body or "").rstrip()
    if b.endswith(DISCLAIMER):
        b = b[: -len(DISCLAIMER)].rstrip()
    return b


def compose(body: str, *, scrape_date: str | None = None) -> str:
    """Attach the footer block: optional freshness line + the disclaimer.

    Idempotent w.r.t. the disclaimer (won't double it if already present).
    """
    base = _strip_trailing_disclaimer(body)
    footer_lines: list[str] = []
    fresh = freshness_footer(scrape_date)
    if fresh:
        footer_lines.append(fresh)
    footer_lines.append(DISCLAIMER)
    return f"{base}\n\n" + "\n".join(footer_lines)


def _is_not_in_sources(text: str) -> bool:
    return text.strip().lower().startswith("i don't have this information")


# ── Branch formatters ─────────────────────────────────────────────────────
def format_no_source() -> Formatted:
    """NO_SOURCE fallback — anti-hallucination (SC14 / RET-1)."""
    return Formatted(
        answer=compose(NOT_IN_SOURCES),
        source_url=None,
        last_updated=None,
        response_type=ResponseType.NO_SOURCE,
        refused=False,
    )


def format_factual(
    draft: str,
    citation: str | None,
    scrape_date: str | None,
    *,
    max_sentences: int,
) -> Formatted:
    """Enforce the contract on a generated factual answer."""
    body = (draft or "").strip()

    # Empty / whitespace draft → safe fallback (FMT-6, E-7.11).
    if not body or _is_not_in_sources(body):
        return format_no_source()

    # Citation must exist and be in the 20-URL allow-list (FMT-3, E-7.12).
    if not citation or not corpus.is_allowed_url(citation):
        return format_no_source()

    # Final PII-echo scan — never ship leaked PII (PII-10, FMT-10).
    if pii.scan(body).has_pii:
        return format_no_source()

    body = trim_sentences(body, max_sentences)
    return Formatted(
        answer=compose(body, scrape_date=scrape_date),
        source_url=citation,
        last_updated=scrape_date,
        response_type=ResponseType.FACTUAL,
        refused=False,
    )


def format_refusal(body: str) -> Formatted:
    """ADVISORY refusal — educational link citation + footer (E-7.9)."""
    return Formatted(
        answer=compose(body),
        source_url=corpus.EDUCATIONAL_URL,
        last_updated=None,
        response_type=ResponseType.ADVISORY_REFUSAL,
        refused=True,
    )


def format_scope(body: str) -> Formatted:
    """OUT_OF_SCOPE boundary — AMC link citation + footer (E-7.10)."""
    return Formatted(
        answer=compose(body),
        source_url=corpus.AMC_HOME_URL,
        last_updated=None,
        response_type=ResponseType.OUT_OF_SCOPE,
        refused=False,
    )


def format_pii(body: str) -> Formatted:
    """PII rejection — no citation, footer present (E-7.3)."""
    return Formatted(
        answer=compose(body),
        source_url=None,
        last_updated=None,
        response_type=ResponseType.PII_REJECTED,
        refused=True,
    )


# Transient-error message for LLM timeouts/5xx — a retry prompt, never a
# fabricated answer (SYS-1, E-8.6).
SERVICE_BUSY_MESSAGE = (
    "I'm having trouble reaching the answer service right now. Please try your "
    "question again in a moment."
)


def format_error() -> Formatted:
    """Graceful transient-error response (200, no fabrication)."""
    return Formatted(
        answer=compose(SERVICE_BUSY_MESSAGE),
        source_url=None,
        last_updated=None,
        response_type=ResponseType.ERROR,
        refused=False,
    )
