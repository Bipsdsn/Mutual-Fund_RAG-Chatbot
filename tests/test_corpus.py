"""Phase 1 tests for corpus configuration (Docs/evals.md E-1.1 .. E-1.6).

Pure data-loading tests; no network, no Groq key required.
Run with: pytest tests/test_corpus.py
"""

from __future__ import annotations

from backend import corpus


def test_exactly_20_unique_urls():
    """E-1.1 (Gate) / SC9: exactly 20 unique corpus URLs."""
    urls = [s["url"] for s in corpus.SOURCES]
    assert len(urls) == 20
    assert len(set(urls)) == 20
    assert len(corpus.ALLOWED_URLS) == 20


def test_all_domains_official():
    """E-1.2 (Gate) / SC10: every URL is on an official domain."""
    for s in corpus.SOURCES:
        host = s["url"].split("://", 1)[-1].split("/", 1)[0].lower()
        assert host in corpus.OFFICIAL_DOMAINS, f"Non-official domain: {host}"


def test_corpus_validates_clean():
    """E-1.3: schema completeness + valid enums → no problems reported."""
    problems = corpus.validate_corpus()
    assert problems == [], f"Corpus problems: {problems}"


def test_source_type_spread():
    """E-1.4: 6 groww + 8 amc + 3 sebi + 3 amfi."""
    counts = corpus.source_type_counts()
    assert counts == {
        "groww_scheme_page": 6,
        "amc_official": 8,
        "sebi": 3,
        "amfi": 3,
    }


def test_alias_resolution_flexi_cap():
    """E-1.5 / RET-6: 'HDFC Equity Fund' resolves to the Flexi Cap canonical name."""
    assert (
        corpus.resolve_scheme("what is the expense ratio of HDFC Equity Fund?")
        == "HDFC Flexi Cap Fund Direct Growth"
    )


def test_short_form_aliases_map():
    """E-1.6: short forms each map to a covered scheme."""
    cases = {
        "mid cap": "HDFC Mid Cap Fund Direct Growth",
        "elss": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
        "gold etf": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
        "small cap": "HDFC Small Cap Fund Direct Growth",
        "large cap": "HDFC Large Cap Fund Direct Growth",
    }
    for text, expected in cases.items():
        assert corpus.resolve_scheme(text) == expected, f"{text!r} did not resolve"


def test_unknown_scheme_returns_none():
    """RET-6 / SCO-1: a non-covered scheme resolves to None."""
    assert corpus.resolve_scheme("HDFC Balanced Advantage Fund") is None
    assert corpus.resolve_scheme("what's the weather today") is None


def test_longest_alias_wins():
    """Disambiguation: a full name should resolve to its own scheme, not a substring alias."""
    assert (
        corpus.resolve_scheme("HDFC Mid Cap Fund Direct Growth")
        == "HDFC Mid Cap Fund Direct Growth"
    )


def test_citation_allow_list_check():
    """Formatter dependency: is_allowed_url accepts corpus URLs, rejects others."""
    a_corpus_url = next(iter(corpus.ALLOWED_URLS))
    assert corpus.is_allowed_url(a_corpus_url) is True
    assert corpus.is_allowed_url("https://moneycontrol.com/whatever") is False
