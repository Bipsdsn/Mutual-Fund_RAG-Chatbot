"""Phase 7 tests for the Response Formatter + responders (Docs/evals.md E-7.x).

Pure/deterministic — no Groq, no Chroma. Verifies the output contract holds on
every branch: ≤3 sentences, exactly one corpus citation, footer present, no PII
echoed, and safe NO_SOURCE fallbacks.
"""

from __future__ import annotations

from backend import corpus, formatter
from backend.models import ResponseType
from backend.responders import refusal, scope

MID_CAP_URL = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"


# ── Decimal/URL-aware sentence counting (the Phase-7 gotcha) ──────────────
def test_decimals_and_urls_not_counted_as_sentence_breaks():
    text = (
        "The NAV is 1234.56 today. The expense ratio is 0.74%. "
        "See https://investor.sebi.gov.in/riskometer.html now."
    )
    assert len(formatter.split_sentences(text)) == 3


def test_single_decimal_answer_is_one_sentence():
    assert len(formatter.split_sentences("The expense ratio is 0.74%.")) == 1


# ── E-7.2 (Gate): trim to ≤3 sentences ────────────────────────────────────
def test_trim_long_draft_to_three_sentences():
    draft = "One. Two. Three. Four. Five."
    out = formatter.format_factual(draft, MID_CAP_URL, "2026-06-23", max_sentences=3)
    # Body (before footer) must have at most 3 sentences.
    body = out.answer.split("\n\n")[0]
    assert len(formatter.split_sentences(body)) == 3
    assert "Four" not in body and "Five" not in body


# ── E-7.1 (Gate): exactly one citation, in the allow-list ─────────────────
def test_factual_citation_in_allowlist():
    out = formatter.format_factual("Expense ratio is 0.74%.", MID_CAP_URL, "2026-06-23", max_sentences=3)
    assert out.response_type is ResponseType.FACTUAL
    assert out.source_url == MID_CAP_URL
    assert corpus.is_allowed_url(out.source_url)


# ── E-7.12: out-of-corpus citation → NO_SOURCE ────────────────────────────
def test_bad_citation_falls_back_to_no_source():
    out = formatter.format_factual("Some fact.", "https://evil.example.com/x", "2026-06-23", max_sentences=3)
    assert out.response_type is ResponseType.NO_SOURCE
    assert out.source_url is None


# ── E-7.11: empty / whitespace draft → NO_SOURCE ──────────────────────────
def test_empty_draft_falls_back_to_no_source():
    out = formatter.format_factual("   ", MID_CAP_URL, "2026-06-23", max_sentences=3)
    assert out.response_type is ResponseType.NO_SOURCE


def test_not_in_sources_draft_normalized_to_no_source():
    out = formatter.format_factual(
        "I don't have this information in my sources.", MID_CAP_URL, "2026-06-23", max_sentences=3
    )
    assert out.response_type is ResponseType.NO_SOURCE
    assert out.source_url is None


# ── PII echo scan: leaked PII in draft → NO_SOURCE, never shipped ─────────
def test_pii_in_draft_is_not_shipped():
    out = formatter.format_factual(
        "Contact the manager at john.doe@example.com.", MID_CAP_URL, "2026-06-23", max_sentences=3
    )
    assert out.response_type is ResponseType.NO_SOURCE
    assert "john.doe@example.com" not in out.answer


# ── E-7.3 (Gate): footer present on every branch ──────────────────────────
def test_footer_present_on_every_branch():
    branches = [
        formatter.format_factual("Expense ratio is 0.74%.", MID_CAP_URL, "2026-06-23", max_sentences=3),
        formatter.format_no_source(),
        formatter.format_refusal(refusal.build()),
        formatter.format_scope(scope.build()),
        formatter.format_pii("PII rejected."),
    ]
    for out in branches:
        assert formatter.DISCLAIMER in out.answer


# ── E-7.4: factual footer carries the scrape_date ─────────────────────────
def test_factual_footer_uses_scrape_date():
    out = formatter.format_factual("Expense ratio is 0.74%.", MID_CAP_URL, "2026-06-23", max_sentences=3)
    assert out.last_updated == "2026-06-23"
    assert "Last updated from sources: 2026-06-23" in out.answer


def test_disclaimer_not_duplicated():
    body = "Some answer.\n\nFacts-only. No investment advice."
    composed = formatter.compose(body)
    assert composed.count(formatter.DISCLAIMER) == 1


# ── E-7.9: refusal shape ──────────────────────────────────────────────────
def test_refusal_shape():
    out = formatter.format_refusal(refusal.build())
    assert out.response_type is ResponseType.ADVISORY_REFUSAL
    assert out.refused is True
    assert out.source_url == corpus.EDUCATIONAL_URL
    assert corpus.EDUCATIONAL_URL in out.answer
    assert formatter.DISCLAIMER in out.answer
    # Body (before footer) is concise.
    body = out.answer.split("\n\n")[0]
    assert len(formatter.split_sentences(body)) <= 3


# ── E-7.10: scope shape lists all 6 schemes + AMC link ────────────────────
def test_scope_shape_lists_all_schemes():
    out = formatter.format_scope(scope.build())
    assert out.response_type is ResponseType.OUT_OF_SCOPE
    assert out.source_url == corpus.AMC_HOME_URL
    for name in corpus.COVERED_SCHEMES:
        assert name in out.answer
    assert corpus.AMC_HOME_URL in out.answer
    assert formatter.DISCLAIMER in out.answer


# ── E-7.5: NO_SOURCE fallback text ────────────────────────────────────────
def test_no_source_message_and_footer():
    out = formatter.format_no_source()
    assert out.response_type is ResponseType.NO_SOURCE
    assert "don't have this information" in out.answer.lower()
    assert formatter.DISCLAIMER in out.answer
    assert out.source_url is None
