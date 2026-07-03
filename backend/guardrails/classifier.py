"""Layer 2 — Query Classifier (Phase 6).

Routes a *clean* query (PII already stripped) to one of three labels:

    FACTUAL       → proceed to retrieval + grounded generation
    ADVISORY      → refusal responder (no opinions/predictions/returns; SC2/SC4)
    OUT_OF_SCOPE  → scope responder (uncovered scheme / non-HDFC AMC / off-topic)

Hybrid routing (Docs/data-flow-architecture.md §5.2):
  1. **Rule pass (deterministic):** advisory keyword gate first (zero advisory
     leakage is mandatory — E-6.1), then competitor-AMC / uncovered-scheme
     detection, then factual data-type keywords + scheme-registry match.
  2. **LLM fallback (Groq):** only for genuinely ambiguous queries that the
     rules cannot decide; returns one label. Defaults to FACTUAL when the query
     is borderline-but-answerable (conventions: default-to-factual-if-answerable).

The rule pass is pure/offline and fully unit-tested (E-6.x). The Groq fallback
is injectable (``llm_fn``) so tests stay deterministic and never hit the network.

Hints (``scheme_hint`` / ``data_type_hint``) are extracted for the retriever's
metadata pre-filter (RET-10). ``scheme_hint`` is the canonical scheme name from
the registry; ``data_type_hint`` is a granular fact label (e.g. ``expense_ratio``).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from backend import corpus

log = logging.getLogger("classifier")


class Label(str, Enum):
    """Classifier routing labels (distinct from response_type values)."""

    FACTUAL = "FACTUAL"
    ADVISORY = "ADVISORY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass
class Classification:
    """Result of classifying one query.

    ``label`` drives branch selection; ``scheme_hint`` / ``data_type_hint`` feed
    the retriever; ``reason`` is a short, PII-free tag for telemetry/logging.
    """

    label: Label
    scheme_hint: str | None = None
    data_type_hint: str | None = None
    reason: str = ""


# ── Rule vocabularies ─────────────────────────────────────────────────────

# Advisory / opinion / prediction / return-projection language. Checked FIRST so
# nothing leaks to FACTUAL (E-6.1, ADV-1..10). Judgment adjectives (good/best/
# better/worth) are treated as advisory because they ask for an opinion.
_ADVISORY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bshould\s+(i|we|you)\b",
        r"\bshall\s+i\b",
        r"\bdo\s+you\s+(recommend|suggest)\b",
        r"\brecommend\b",
        r"\bsuggest\b",
        r"\badvise\b|\badvice\b",
        r"\bworth\s+(it|investing|buying|the)\b",
        r"\bis\s+it\s+worth\b",
        r"\bgood\s+(fund|investment|option|choice|idea|buy|time|bet)\b",
        r"\b(a|an)\s+good\b",  # "is it a good fund"
        r"\bbetter\b",
        r"\bbest\s+(fund|option|choice|scheme|investment)\b",
        r"\bwhich\s+(is\s+)?(better|best)\b",
        r"\bpredict\b|\bforecast\b",
        r"\bwill\s+.{0,40}\b(go\s+up|rise|fall|drop|increase|decrease|grow|crash|double)\b",
        r"\b(what|how\s+much)\s+returns?\b",
        r"\breturns?\s+will\b",
        r"\bexpected\s+returns?\b",
        r"\bhow\s+much\s+(will|can|could)\s+i\s+(earn|make|get|gain)\b",
        r"\bhow\s+much\s+(should\s+i|sip|to\s+invest)\b",
        r"\b(add|include)\b.{0,30}\bportfolio\b",
        r"\bmy\s+portfolio\b",
        r"\bis\s+.{0,40}\b(a\s+)?(good|bad|great|safe|risky)\s+(fund|investment|choice|bet)\b",
    )
)

# Competing AMCs / fund houses (anything not HDFC). Word-boundary matched.
_COMPETITOR_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bsbi\b",
        r"\bicici\b",
        r"\baxis\b",
        r"\bnippon\b",
        r"\bkotak\b",
        r"\baditya\s+birla\b|\bbirla\b",
        r"\buti\b",
        r"\bdsp\b",
        r"\bfranklin\b",
        r"\bmirae\b",
        r"\btata\b",
        r"\bl&t\b|\bl\s*&\s*t\b",
        r"\bmotilal\b",
        r"\bquant\b",
        r"\b(parag\s+parikh|ppfas)\b",
        r"\bedelweiss\b",
        r"\binvesco\b",
        r"\bsundaram\b",
        r"\bcanara\b",
        r"\bbaroda\b",
        r"\bbandhan\b",
        r"\bhsbc\b",
        r"\bbajaj\b",
        r"\bwhiteoak\b|\bwhite\s+oak\b",
        r"\b360\s*one\b",
        r"\bnavi\b",
    )
)

# Uncovered HDFC (or generic) scheme/category names. Only consulted when the
# query does NOT resolve to one of the 6 covered schemes (E-6.3 SCO-1).
_UNCOVERED_SCHEME_KEYWORDS: tuple[str, ...] = (
    "balanced advantage",
    "balanced fund",
    "hybrid",
    "liquid fund",
    "debt fund",
    "banking and psu",
    "banking & psu",
    "infrastructure",
    "dividend yield",
    "focused",
    "multi cap",
    "multi-cap",
    "multicap",
    "multi asset",
    "multi-asset",
    "credit risk",
    "corporate bond",
    "overnight",
    "money market",
    "arbitrage",
    "index fund",
    "nifty 50 index",
    "sensex",
    "top 100",
    "capital builder",
    "retirement",
    "children",
    "pharma",
    "technology fund",
    "defence",
    "low duration",
    "short term",
    "ultra short",
    "gilt",
    "floating rate",
    "dynamic bond",
    "value fund",
    "contra",
)

# Granular data-type keywords → ``data_type_hint`` (ordered: specific first).
# The label values are the granular fact names used by evals/telemetry.
_DATA_TYPE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("expense_ratio", ("expense ratio", "total expense ratio")),
    ("exit_load", ("exit load", "exit fee")),
    ("lock_in", ("lock-in", "lock in", "lockin")),
    ("stamp_duty", ("stamp duty",)),
    ("sip", ("sip", "systematic investment", "minimum sip")),
    ("lumpsum", ("lumpsum", "lump sum", "minimum investment", "minimum lumpsum", "one-time investment")),
    ("nav", ("nav", "net asset value")),
    ("aum", ("aum", "fund size", "assets under management")),
    ("fund_manager", ("fund manager", "managed by", "manager of", "who manages")),
    ("benchmark", ("benchmark", "benchmarked")),
    ("launch_date", ("launch date", "inception date", "inception", "launched")),
    ("riskometer", ("riskometer", "risk level", "risk category")),
    ("tax", ("taxation", "ltcg", "stcg", "capital gains tax", "how is .* taxed", "tax on",
             "tax deduction", "tax benefit", "tax saving", "section 80c", "80c", "deduction")),
    ("category", ("scheme category", "fund category", "type of scheme", "category of")),
    ("statement_guide", (
        "capital gains statement",
        "capital gain statement",
        "consolidated account statement",
        "account statement",
        "cas",
        "how to download",
        "statement",
    )),
)

# General MF concept questions answerable from AMFI/SEBI pages (E-6.9, SCO-6),
# even without a covered scheme mentioned.
_GENERAL_CONCEPT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bwhat\s+(is|are)\b.{0,60}\b(mutual\s+fund|expense\s+ratio|exit\s+load|nav|sip|"
        r"riskometer|lock[\s-]?in|elss|aum|benchmark|direct\s+plan|fund\s+of\s+fund|"
        r"net\s+asset\s+value|stamp\s+duty|fund\s+manager)\b",
        r"\b(explain|define|meaning\s+of)\b.{0,40}\b(mutual\s+fund|expense\s+ratio|sip|nav|"
        r"riskometer|lock[\s-]?in|elss|benchmark)\b",
        r"\bwhat\s+(is|are)\s+the\s+(types|categories)\s+of\s+mutual\s+funds?\b",
        r"\bhow\s+(do|does)\s+(a\s+)?mutual\s+funds?\s+work\b",
    )
)

# Weak signal that the query is even about mutual funds (used to separate
# "ambiguous MF query" from "off-topic" before the LLM fallback).
_MF_SIGNAL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bmutual\s+fund\b",
        r"\bhdfc\b",
        r"\bscheme\b",
        r"\bfund\b",
        r"\bnav\b",
        r"\bsip\b",
        r"\belss\b",
        r"\binvest(ment|ing|ed)?\b",
        r"\bportfolio\b",
        r"\bgrowth\s+plan\b",
        r"\bdirect\s+plan\b",
    )
)

# Educational / scope links (must be in the 20-URL allow-list). Sourced from
# corpus so the URLs live in one place (used by Phase-6 wiring + Phase-7
# responders). Phase 7 responders harden the full message.
EDUCATIONAL_LINK = corpus.EDUCATIONAL_URL
AMC_SCOPE_LINK = corpus.AMC_HOME_URL


# ── Detection helpers (pure) ──────────────────────────────────────────────
def _matches_any(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(p.search(text) for p in patterns)


def is_advisory(query: str) -> bool:
    """True iff the query asks for advice/opinion/prediction/return projection."""
    return _matches_any(query, _ADVISORY_PATTERNS)


def mentions_competitor(query: str) -> bool:
    """True iff a non-HDFC AMC / fund house is named (SCO-2)."""
    return _matches_any(query, _COMPETITOR_PATTERNS)


def mentions_uncovered_scheme(query: str) -> bool:
    """True iff an uncovered scheme/category keyword appears (SCO-1)."""
    low = query.lower()
    return any(kw in low for kw in _UNCOVERED_SCHEME_KEYWORDS)


def detect_data_type(query: str) -> str | None:
    """Return the first matching granular data-type hint, or None."""
    low = query.lower()
    for data_type, keywords in _DATA_TYPE_KEYWORDS:
        for kw in keywords:
            # A few keywords carry a regex wildcard (e.g. "how is .* taxed").
            if ".*" in kw:
                if re.search(kw, low):
                    return data_type
            elif kw in low:
                return data_type
    return None


def is_general_concept(query: str) -> bool:
    """True iff this is a general MF-concept question (answerable from AMFI/SEBI)."""
    return _matches_any(query, _GENERAL_CONCEPT_PATTERNS)


def has_mf_signal(query: str) -> bool:
    """True iff the query looks like it is about mutual funds at all."""
    return _matches_any(query, _MF_SIGNAL_PATTERNS)


# ── LLM fallback (injectable; lazy Groq) ──────────────────────────────────
_FALLBACK_SYSTEM = (
    "You are a router for a facts-only HDFC Mutual Fund assistant. "
    "Classify the user's message into exactly one label:\n"
    "FACTUAL = asks for a verifiable fact about a mutual fund (expense ratio, "
    "exit load, NAV, AUM, manager, lock-in, tax rules, how to get a statement, "
    "or a general mutual-fund concept).\n"
    "ADVISORY = asks for an opinion, recommendation, prediction, return "
    "projection, comparison of 'which is better', or personal-finance advice.\n"
    "OUT_OF_SCOPE = about a non-HDFC fund house, an HDFC scheme we don't cover, "
    "or anything not about mutual funds.\n"
    "Reply with ONLY one word: FACTUAL, ADVISORY, or OUT_OF_SCOPE."
)


def _default_llm_fallback(query: str) -> Label:
    """Call Groq for an ambiguous query; default to FACTUAL on any failure."""
    try:
        from backend.rag import generator

        raw = generator.call_groq(_FALLBACK_SYSTEM, query, max_tokens=4, temperature=0.0)
        token = (raw or "").strip().upper()
        for label in (Label.ADVISORY, Label.OUT_OF_SCOPE, Label.FACTUAL):
            if label.value in token:
                return label
    except Exception as exc:  # noqa: BLE001 - never fail the request on router error
        log.warning("classifier LLM fallback unavailable: %s", type(exc).__name__)
    # Borderline-but-answerable defaults to FACTUAL (retrieval threshold is the
    # final anti-hallucination guard anyway).
    return Label.FACTUAL


# ── Public entry point ────────────────────────────────────────────────────
def classify(
    query: str,
    *,
    llm_fn: Callable[[str], Label] | None = None,
) -> Classification:
    """Classify ``query`` into FACTUAL / ADVISORY / OUT_OF_SCOPE.

    ``llm_fn(query) -> Label`` is injectable for tests; when omitted, the real
    Groq fallback is used (only for genuinely ambiguous queries).
    """
    if not query or not query.strip():
        return Classification(Label.OUT_OF_SCOPE, reason="empty")

    text = query.strip()

    # 1) Advisory gate first — zero leakage is mandatory (E-6.1).
    if is_advisory(text):
        return Classification(Label.ADVISORY, reason="advisory_rule")

    # 2) Competing fund house named → out of scope (E-6.4, SCO-2).
    if mentions_competitor(text):
        return Classification(Label.OUT_OF_SCOPE, reason="competitor_amc")

    # 3) Resolve to a covered scheme (alias-aware).
    scheme_hint = corpus.resolve_scheme(text)

    # 4) Uncovered scheme/category named (and not a covered scheme) → OOS (E-6.3).
    if scheme_hint is None and mentions_uncovered_scheme(text):
        return Classification(Label.OUT_OF_SCOPE, reason="uncovered_scheme")

    # 5) Factual signals: a data-type keyword, a covered scheme, or a general
    #    MF concept question all route to FACTUAL (E-6.2, E-6.8, E-6.9).
    data_type_hint = detect_data_type(text)
    if data_type_hint or scheme_hint or is_general_concept(text):
        return Classification(
            Label.FACTUAL,
            scheme_hint=scheme_hint,
            data_type_hint=data_type_hint,
            reason="factual_rule",
        )

    # 6) No mutual-fund signal at all → out of scope (E-6.5, SCO-5).
    if not has_mf_signal(text):
        return Classification(Label.OUT_OF_SCOPE, reason="off_topic")

    # 7) Ambiguous but MF-related → LLM fallback (default FACTUAL).
    fallback = llm_fn or _default_llm_fallback
    label = fallback(text)
    return Classification(
        label,
        scheme_hint=scheme_hint,
        data_type_hint=data_type_hint,
        reason="llm_fallback",
    )
