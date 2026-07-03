"""Phase 3 offline tests for the retrieval core (Docs/evals.md E-3.x).

Pure-logic tests with an injected fake collection + embed_fn — no Chroma, no
sentence-transformers, no Groq key. The full 17-type retrieval sweep (E-3.3) is
verified manually against the live index.
"""

from __future__ import annotations

from backend.rag import retriever
from backend.rag.retriever import RetrievedChunk


def _chunk(score, source_type="groww_scheme_page", url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth", scheme="HDFC Mid Cap Fund Direct Growth", dtype="expense_ratio", date="2026-06-23"):
    return RetrievedChunk(
        text="x", score=score, source_url=url, source_type=source_type,
        scheme_name=scheme, data_type=dtype, scrape_date=date,
    )


# ── distance/threshold ────────────────────────────────────────────────────
def test_distance_to_score():
    assert retriever.distance_to_score(0.0) == 1.0
    assert abs(retriever.distance_to_score(0.4) - 0.6) < 1e-9


def test_passes_threshold():
    assert retriever.passes_threshold(0.6, 0.35) is True
    assert retriever.passes_threshold(0.2, 0.35) is False


# ── where-filter building (RET-10) ────────────────────────────────────────
def test_build_where_variants():
    assert retriever.build_where(None, None) is None
    assert retriever.build_where("HDFC Mid Cap Fund Direct Growth", None) == {
        "scheme_name": "HDFC Mid Cap Fund Direct Growth"
    }
    both = retriever.build_where("HDFC Mid Cap Fund Direct Growth", "expense_ratio")
    assert "$and" in both and len(both["$and"]) == 2


# ── citation selection + tie-break (D-21) ─────────────────────────────────
def test_citation_picks_highest_score():
    chunks = [_chunk(0.5), _chunk(0.9, url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth", scheme="HDFC Large Cap Fund Direct Growth")]
    assert retriever.rank_and_select_citation(chunks).endswith("hdfc-large-cap-fund-direct-growth")


def test_citation_tie_break_by_source_priority():
    # Equal scores: groww_scheme_page should beat amfi.
    amfi = _chunk(0.80, source_type="amfi", url="https://www.amfiindia.com/investor-corner/investor-center/investor-faq.html")
    groww = _chunk(0.80, source_type="groww_scheme_page")
    assert retriever.rank_and_select_citation([amfi, groww]) == groww.source_url


def test_citation_must_be_in_corpus():
    bogus = _chunk(0.95, url="https://moneycontrol.com/x")
    assert retriever.rank_and_select_citation([bogus]) is None


# ── result assembly (E-3.4 below-threshold → no match) ────────────────────
def test_assemble_below_threshold_no_match():
    res = retriever.assemble_result([_chunk(0.20)], threshold=0.35)
    assert res.has_match is False
    assert res.citation is None


def test_assemble_above_threshold_has_citation():
    res = retriever.assemble_result([_chunk(0.80)], threshold=0.35)
    assert res.has_match is True
    assert res.citation.endswith("hdfc-mid-cap-fund-direct-growth")
    assert res.scrape_date == "2026-06-23"


def test_assemble_empty_chunks():
    res = retriever.assemble_result([], threshold=0.35)
    assert res.has_match is False and res.chunks == []


# ── parse Chroma result shape ─────────────────────────────────────────────
def test_parse_query_result():
    raw = {
        "ids": [["groww_mid_cap_0001"]],
        "documents": [["expense ratio 0.74%"]],
        "metadatas": [[{
            "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "source_type": "groww_scheme_page",
            "scheme_name": "HDFC Mid Cap Fund Direct Growth",
            "data_type": "expense_ratio",
            "scrape_date": "2026-06-23",
        }]],
        "distances": [[0.1]],
    }
    chunks = retriever.parse_query_result(raw)
    assert len(chunks) == 1
    assert abs(chunks[0].score - 0.9) < 1e-9
    assert chunks[0].scheme_name == "HDFC Mid Cap Fund Direct Growth"


# ── end-to-end retrieve() with injected fakes ─────────────────────────────
class _FakeCollection:
    """Minimal Chroma-like stub for retrieve()."""

    def __init__(self, result):
        self._result = result
        self.calls = []

    def query(self, query_embeddings, n_results, where=None):
        self.calls.append({"n_results": n_results, "where": where})
        return self._result


def test_retrieve_factual_match():
    raw = {
        "ids": [["groww_mid_cap_0001"]],
        "documents": [["expense ratio 0.74%"]],
        "metadatas": [[{
            "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "source_type": "groww_scheme_page",
            "scheme_name": "HDFC Mid Cap Fund Direct Growth",
            "data_type": "expense_ratio",
            "scrape_date": "2026-06-23",
        }]],
        "distances": [[0.1]],
    }
    coll = _FakeCollection(raw)
    res = retriever.retrieve(
        "expense ratio of HDFC Mid Cap?",
        top_k=5, threshold=0.35,
        scheme_hint="HDFC Mid Cap Fund Direct Growth", data_type_hint="expense_ratio",
        collection=coll, embed_fn=lambda q: [0.0, 0.1, 0.2],
    )
    assert res.has_match is True
    assert res.citation.endswith("hdfc-mid-cap-fund-direct-growth")
    # filtered query was attempted with a where clause
    assert coll.calls[0]["where"] is not None


def test_retrieve_empty_query():
    res = retriever.retrieve("   ", collection=_FakeCollection({}), embed_fn=lambda q: [0.0])
    assert res.has_match is False


def test_retrieve_falls_back_when_filter_empty():
    empty = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    full = {
        "ids": [["groww_mid_cap_0001"]],
        "documents": [["expense ratio 0.74%"]],
        "metadatas": [[{
            "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "source_type": "groww_scheme_page",
            "scheme_name": "HDFC Mid Cap Fund Direct Growth",
            "data_type": "expense_ratio",
            "scrape_date": "2026-06-23",
        }]],
        "distances": [[0.1]],
    }

    class _TwoStage:
        def __init__(self):
            self.n = 0

        def query(self, query_embeddings, n_results, where=None):
            self.n += 1
            return empty if where is not None else full

    res = retriever.retrieve(
        "expense ratio", top_k=5, threshold=0.35,
        scheme_hint="HDFC Mid Cap Fund Direct Growth",
        collection=_TwoStage(), embed_fn=lambda q: [0.0],
    )
    assert res.has_match is True
