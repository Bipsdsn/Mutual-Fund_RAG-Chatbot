"""Tests for the structured fact store + ingestion writer (hybrid retrieval, D-65).

Pure/deterministic — no Groq, no Chroma. Covers exact lookup, sentence
rendering, citation validity, and the extract→facts transform.
"""

from __future__ import annotations

from backend import corpus
from backend.rag import facts
from ingestion import build_facts


# ── Seeded regulatory facts: lock-in for every scheme ─────────────────────
def test_elss_lock_in_is_three_years():
    fact = facts.lookup("HDFC ELSS Tax Saver Fund Direct Plan Growth", "lock_in")
    assert fact is not None
    assert fact.value == "3 years"
    assert corpus.is_allowed_url(fact.source_url)
    assert "3 years" in facts.render(fact)
    assert "lock-in period" in facts.render(fact).lower()


def test_non_elss_has_no_lock_in():
    fact = facts.lookup("HDFC Mid Cap Fund Direct Growth", "lock_in")
    assert fact is not None
    assert fact.value == "None"
    assert "no lock-in period" in facts.render(fact).lower()


def test_every_scheme_has_a_lock_in_fact():
    for scheme in corpus.SCHEMES:
        assert facts.has_fact(scheme["canonical_name"], "lock_in")


# ── ELSS Section-80C tax benefit (alias: classifier hint "tax") ───────────
def test_elss_tax_benefit_via_alias():
    fact = facts.lookup("HDFC ELSS Tax Saver Fund Direct Plan Growth", "tax")
    assert fact is not None
    assert "1.5 lakh" in fact.value and "80C" in fact.value
    assert corpus.is_allowed_url(fact.source_url)
    assert "tax deduction" in facts.render(fact).lower()


def test_non_elss_has_no_tax_benefit():
    assert facts.lookup("HDFC Mid Cap Fund Direct Growth", "tax") is None


# ── Misses return None (fall back to semantic search) ─────────────────────
def test_unknown_scheme_or_type_returns_none():
    assert facts.lookup(None, "lock_in") is None
    assert facts.lookup("HDFC Mid Cap Fund Direct Growth", None) is None
    assert facts.lookup("HDFC Mid Cap Fund Direct Growth", "benchmark") is None  # never seeded/scraped


# ── Generic render for numeric facts ──────────────────────────────────────
def test_render_generic_numeric():
    rec = facts.FactRecord(
        scheme_name="HDFC Mid Cap Fund Direct Growth",
        data_type="expense_ratio",
        value="0.74%",
        source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        scrape_date="2026-06-23",
        display_name="HDFC Mid Cap Fund",
    )
    assert facts.render(rec) == "The expense ratio of HDFC Mid Cap Fund is 0.74%."


# ── Ingestion transform: extract fields → fact entries ────────────────────
def test_to_fact_entries_maps_known_numeric_fields():
    fields = {
        "expense_ratio": "0.74",
        "nav": "228.45",
        "exit_load": "1% if redeemed within 1 year",  # not a clean numeric → skipped
    }
    url = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    entries = build_facts.to_fact_entries(fields, source_url=url, scrape_date="2026-06-23")

    assert entries["expense_ratio"]["value"] == "0.74%"
    assert entries["nav"]["value"] == "₹228.45"
    assert entries["expense_ratio"]["source_url"] == url
    assert "exit_load" not in entries  # only known citable numeric fields kept


def test_to_fact_entries_skips_unknown_fields():
    entries = build_facts.to_fact_entries({"benchmark": "Nifty Midcap 150"}, source_url="x", scrape_date="d")
    assert entries == {}
