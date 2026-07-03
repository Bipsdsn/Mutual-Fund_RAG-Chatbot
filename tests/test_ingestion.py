"""Phase 2 offline tests for the ingestion pipeline.

Covers the deterministic, dependency-free parts (clean, extract, chunk/metadata,
fetch dispatch). The live scrape + embed run is verified manually (eval E-2.x)
since it needs network + heavy deps.
"""

from __future__ import annotations

import pytest

from ingestion import clean as cleaner
from ingestion import extract as extractor
from ingestion import scrape
from ingestion import chunk_embed


# ── clean.py (ING-5: ₹/% preserved, whitespace normalized) ────────────────
def test_normalize_preserves_rupee_and_percent():
    raw = "Expense   ratio\u00a0is\t0.74%   and  AUM ₹28,500 crore"
    out = cleaner.normalize_text(raw)
    assert "₹" in out
    assert "0.74%" in out
    assert "  " not in out  # collapsed


def test_normalize_collapses_blank_lines():
    raw = "line1\n\n\n\n\nline2"
    out = cleaner.normalize_text(raw)
    assert out == "line1\n\nline2"


def test_clean_html_strips_script_nav():
    pytest.importorskip("bs4")  # installed via requirements.txt; skip if absent
    html = (
        "<html><head><style>.x{}</style></head><body>"
        "<nav>menu home</nav><script>var a=1;</script>"
        "<main>Expense ratio is 0.74%</main><footer>copyright</footer>"
        "</body></html>"
    )
    out = cleaner.clean(html, is_text_extracted=False)
    assert "Expense ratio is 0.74%" in out
    assert "menu home" not in out
    assert "var a" not in out
    assert "copyright" not in out


# ── extract.py (best-effort fields; never fabricate — ING-4) ──────────────
def test_extract_expense_ratio_and_sip():
    text = "The expense ratio is 0.74%. Minimum SIP ₹100. Fund size ₹28,500 crore."
    fields = extractor.extract_fields(text)
    assert fields.get("expense_ratio") == "0.74"
    assert fields.get("min_sip") == "100"
    assert fields.get("aum", "").startswith("28,500")


def test_extract_returns_empty_when_absent():
    assert extractor.extract_fields("") == {}
    assert "expense_ratio" not in extractor.extract_fields("no numeric facts here")


def test_facts_summary_includes_scheme():
    fields = {"expense_ratio": "0.74"}
    summary = extractor.facts_summary(fields, "HDFC Mid Cap Fund")
    assert summary.startswith("HDFC Mid Cap Fund:")
    assert "expense ratio = 0.74" in summary


# ── chunk_embed.py (metadata completeness — E-2.3; data_type inference) ────
SOURCE = {
    "id": "groww_mid_cap",
    "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "source_type": "groww_scheme_page",
    "scheme_name": "HDFC Mid Cap Fund Direct Growth",
    "scheme_category": "Equity — Mid Cap",
    "default_data_type": "scheme_facts",
}


def test_chunk_metadata_complete():
    chunks = chunk_embed.make_chunks(
        "Expense ratio is 0.74%. " * 100, SOURCE, "2026-06-23", prefix="summary line"
    )
    assert len(chunks) >= 1
    required = {
        "source_url", "source_type", "scheme_name", "scheme_category",
        "data_type", "scrape_date", "chunk_index",
    }
    for c in chunks:
        assert required.issubset(c.metadata.keys())
        assert c.metadata["scrape_date"] == "2026-06-23"
        assert c.metadata["source_url"] == SOURCE["url"]
        assert c.id.startswith("groww_mid_cap_")


def test_chunk_indices_sequential():
    chunks = chunk_embed.make_chunks("word " * 1000, SOURCE, "2026-06-23")
    indices = [c.metadata["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))


def test_data_type_inference():
    assert chunk_embed.infer_data_type("the expense ratio is 0.74%", "scheme_facts") == "expense_ratio"
    assert chunk_embed.infer_data_type("3 year lock-in applies", "scheme_facts") == "lock_in"
    assert chunk_embed.infer_data_type("nothing relevant", "scheme_facts") == "scheme_facts"


def test_metadata_no_none_values():
    """Chroma rejects None metadata; general pages must use '' not None."""
    general = {
        "id": "amfi_faq", "url": "https://www.amfiindia.com/x",
        "source_type": "amfi", "scheme_name": None, "scheme_category": None,
        "default_data_type": "investor_education",
    }
    chunks = chunk_embed.make_chunks("What is a mutual fund? " * 50, general, "2026-06-23")
    for c in chunks:
        assert c.metadata["scheme_name"] == ""
        assert c.metadata["scheme_category"] == ""
        assert all(v is not None for v in c.metadata.values())


# ── scrape.py dispatch + graceful failure (ING-8) ─────────────────────────
def test_fetch_uses_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(scrape, "RAW_CACHE_DIR", tmp_path)
    # Pre-seed cache
    (tmp_path / "groww_mid_cap.html").write_text("<html>cached</html>", encoding="utf-8")
    src = {"id": "groww_mid_cap", "url": "https://groww.in/x", "fetch_mode": "html_static"}
    doc = scrape.fetch(src, use_cache=True, polite_delay=False)
    assert "cached" in doc.content
    assert doc.is_text_extracted is False


def test_fetch_unknown_mode_raises():
    src = {"id": "x", "url": "https://groww.in/x", "fetch_mode": "carrier_pigeon"}
    with pytest.raises(scrape.FetchError):
        scrape.fetch(src, use_cache=False, polite_delay=False)


def test_fetch_failure_is_fetcherror(monkeypatch, tmp_path):
    monkeypatch.setattr(scrape, "RAW_CACHE_DIR", tmp_path)

    def boom(url):
        raise RuntimeError("network down")

    monkeypatch.setitem(scrape._FETCHERS, "html_static", boom)
    src = {"id": "x", "url": "https://groww.in/x", "fetch_mode": "html_static"}
    with pytest.raises(scrape.FetchError):
        scrape.fetch(src, use_cache=False, polite_delay=False)
