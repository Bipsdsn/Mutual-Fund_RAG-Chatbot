"""Phase 4 API tests for POST /api/query (eval E-4.1 happy path, NO_SOURCE path).

Uses FastAPI's TestClient. Retrieval + generation are monkeypatched so no Chroma
or Groq is touched. Skips if fastapi/httpx aren't installed in this environment
(they ship via requirements.txt).
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from backend import corpus, main  # noqa: E402
from backend.rag import retriever  # noqa: E402
from backend.rag.retriever import RetrievedChunk, RetrievalResult  # noqa: E402

client = TestClient(main.app)


def _match_result():
    chunk = RetrievedChunk(
        text="The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.74%.",
        score=0.82,
        source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        source_type="groww_scheme_page",
        scheme_name="HDFC Mid Cap Fund Direct Growth",
        data_type="expense_ratio",
        scrape_date="2026-06-23",
    )
    return RetrievalResult(
        chunks=[chunk], best_score=0.82, has_match=True,
        citation=chunk.source_url, scrape_date="2026-06-23",
    )


def test_factual_happy_path(monkeypatch):
    """E-4.1: factual query → grounded answer + correct citation + scrape_date."""
    monkeypatch.setattr(retriever, "retrieve", lambda q, **k: _match_result())
    monkeypatch.setattr(main.retriever, "retrieve", lambda q, **k: _match_result())
    monkeypatch.setattr(main.generator, "generate", lambda q, chunks, **k: "The riskometer level is Very High.")

    # A riskometer question is FACTUAL but has no structured fact, so it flows
    # through retrieval + generation (both monkeypatched).
    resp = client.post("/api/query", json={"query": "what is the riskometer level of HDFC Mid Cap Fund?"})
    assert resp.status_code == 200
    body = resp.json()
    # Formatter appends the footer block; the answer body is still present.
    assert "The riskometer level is Very High." in body["answer"]
    assert "Facts-only. No investment advice." in body["answer"]
    assert "Last updated from sources: 2026-06-23" in body["answer"]
    assert body["source_url"].endswith("hdfc-mid-cap-fund-direct-growth")
    assert body["last_updated"] == "2026-06-23"
    assert body["response_type"] == "FACTUAL"
    assert body["refused"] is False


def test_no_source_path(monkeypatch):
    """Below-threshold retrieval → NO_SOURCE fallback, no fabrication (SC14).

    Uses a FACTUAL covered-scheme query so it routes past the classifier into
    retrieval, which is monkeypatched to report no match.
    """
    monkeypatch.setattr(main.retriever, "retrieve", lambda q, **k: RetrievalResult(has_match=False))

    resp = client.post("/api/query", json={"query": "what is the stamp duty on HDFC Mid Cap Fund?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_type"] == "NO_SOURCE"
    assert body["source_url"] is None
    assert "don't have this information" in body["answer"].lower()


def test_advisory_refused_before_retrieval(monkeypatch):
    """E-6.1: advisory query → ADVISORY_REFUSAL; retrieval never reached (SC4)."""
    def _should_not_run(*a, **k):
        raise AssertionError("retrieve must not be called on advisory input")

    monkeypatch.setattr(main.retriever, "retrieve", _should_not_run)

    resp = client.post("/api/query", json={"query": "Should I invest in HDFC Mid Cap Fund?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_type"] == "ADVISORY_REFUSAL"
    assert body["refused"] is True
    assert body["source_url"] == "https://www.amfiindia.com/investor"


def test_structured_fact_answers_without_retrieval(monkeypatch):
    """Hybrid D-65: ELSS lock-in is answered from the fact store; no retrieval/Groq."""
    def _should_not_run(*a, **k):
        raise AssertionError("retrieve must not be called when a structured fact exists")

    monkeypatch.setattr(main.retriever, "retrieve", _should_not_run)

    resp = client.post("/api/query", json={"query": "what is the lock-in period of HDFC ELSS Tax Saver?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_type"] == "FACTUAL"
    assert "3 years" in body["answer"]
    assert body["source_url"] in corpus.ALLOWED_URLS
    assert "Facts-only. No investment advice." in body["answer"]


def test_out_of_scope_before_retrieval(monkeypatch):
    """E-6.3/E-6.4: uncovered scheme / other AMC → OUT_OF_SCOPE; no retrieval."""
    def _should_not_run(*a, **k):
        raise AssertionError("retrieve must not be called on out-of-scope input")

    monkeypatch.setattr(main.retriever, "retrieve", _should_not_run)

    resp = client.post("/api/query", json={"query": "expense ratio of HDFC Balanced Advantage?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_type"] == "OUT_OF_SCOPE"
    assert body["refused"] is False
    assert body["source_url"] == "https://www.hdfcfund.com/mutual-funds/factsheets"


def test_empty_query_rejected_by_validation():
    """Empty query → 422 validation error (INP-1)."""
    resp = client.post("/api/query", json={"query": ""})
    assert resp.status_code == 422


def test_pii_short_circuits_before_retrieval(monkeypatch):
    """E-5.12: PII guard runs first — retrieval/generation are never reached."""
    called = {"retrieve": False}

    def _should_not_run(*a, **k):
        called["retrieve"] = True
        raise AssertionError("retrieve must not be called on PII input")

    monkeypatch.setattr(main.retriever, "retrieve", _should_not_run)

    resp = client.post("/api/query", json={"query": "my PAN is ABCDE1234F, expense ratio?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_type"] == "PII_REJECTED"
    assert body["refused"] is True
    assert body["source_url"] is None
    # No echo of the PAN value anywhere in the response.
    assert "ABCDE1234F" not in body["answer"]
    assert called["retrieve"] is False
