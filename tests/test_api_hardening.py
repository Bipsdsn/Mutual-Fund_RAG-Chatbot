"""Phase 8 tests — API hardening (Docs/evals.md E-8.x).

Health/examples/meta endpoints, graceful 503 on index-down, safe retry message
on Groq failure, malformed-body validation, and CORS. No real Chroma/Groq.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from backend import corpus, main  # noqa: E402
from backend.rag import generator  # noqa: E402
from backend.rag.retriever import RetrievedChunk, RetrievalResult  # noqa: E402

client = TestClient(main.app)


def _match_result():
    chunk = RetrievedChunk(
        text="HDFC Mid Cap expense ratio is 0.74%.",
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


# ── E-8.1: health reports index status ────────────────────────────────────
def test_health_ok_when_index_loaded(monkeypatch):
    monkeypatch.setattr(main.retriever, "get_index_info", lambda: {"loaded": True, "count": 120, "error": None})
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["index_loaded"] is True
    assert body["chunk_count"] == 120


def test_health_degraded_when_index_missing(monkeypatch):
    monkeypatch.setattr(main.retriever, "get_index_info", lambda: {"loaded": False, "count": None, "error": "NotFound"})
    resp = client.get("/api/health")
    assert resp.status_code == 200  # health itself never fails
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["index_loaded"] is False


# ── E-8.3: examples endpoint returns exactly 3 ────────────────────────────
def test_examples_returns_three():
    resp = client.get("/api/examples")
    assert resp.status_code == 200
    assert len(resp.json()["examples"]) == 3


# ── E-8.4: meta endpoint has 6 schemes + scrape_date key ──────────────────
def test_meta_lists_six_schemes():
    resp = client.get("/api/meta")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scheme_count"] == 6
    assert len(body["schemes"]) == 6
    assert set(body["schemes"]) == set(corpus.COVERED_SCHEMES)
    assert "scrape_date" in body


# ── E-8.2: index down → 503 graceful (no stack trace) ─────────────────────
def test_index_down_returns_503(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("chroma collection missing")

    monkeypatch.setattr(main.retriever, "retrieve", _boom)
    # A riskometer query has no structured fact, so it forces the semantic path.
    resp = client.post("/api/query", json={"query": "what is the riskometer level of HDFC Mid Cap Fund?"})
    assert resp.status_code == 503
    assert "temporarily unavailable" in resp.json()["detail"].lower()


# ── E-8.6: Groq timeout → graceful retry message, never fabricate ─────────
def test_groq_failure_returns_safe_message(monkeypatch):
    monkeypatch.setattr(main.retriever, "retrieve", lambda q, **k: _match_result())

    def _fail(*a, **k):
        raise generator.GroqUnavailable("timeout")

    monkeypatch.setattr(main.generator, "generate", _fail)
    # Riskometer query → semantic path → generation fails → safe ERROR message.
    resp = client.post("/api/query", json={"query": "what is the riskometer level of HDFC Mid Cap Fund?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_type"] == "ERROR"
    assert "try" in body["answer"].lower()
    # No fabricated number in the safe message.
    assert "0.74" not in body["answer"]


# ── E-8.5: malformed body → 422 (not 500) ─────────────────────────────────
def test_missing_query_field_returns_422():
    resp = client.post("/api/query", json={})
    assert resp.status_code == 422


# ── E-8.7: CORS — allowed origin gets the ACAO header ─────────────────────
def test_cors_allows_configured_origin():
    origin = main.settings.allowed_origins[0]
    resp = client.get("/api/meta", headers={"Origin": origin})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == origin
