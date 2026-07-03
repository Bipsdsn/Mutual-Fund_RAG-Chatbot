"""Phase 10 integration tests against the REAL local index (Docs/evals.md
E-3.x / E-10.1 / SC1 / SC14).

Loads the built numpy index (data/local_index) + fastembed and verifies:
- scheme-specific queries retrieve the correct scheme's chunk / citation,
- general concepts retrieve AMFI/SEBI content,
- clearly off-corpus queries fall below threshold → no match (anti-hallucination).

Skips cleanly if the index hasn't been built or fastembed isn't installed, so
the unit suite still runs in a bare environment.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("REQUIRE_SECRETS", "0")

pytest.importorskip("fastembed")

from backend import corpus  # noqa: E402
from backend.rag import local_embed, retriever  # noqa: E402
from backend.rag.local_store import NumpyCollection  # noqa: E402

INDEX_DIR = Path(__file__).resolve().parent.parent / "data" / "local_index"

pytestmark = pytest.mark.skipif(
    not (INDEX_DIR / "records.json").exists(),
    reason="local index not built (run `python -m ingestion.run_ingest_local`)",
)


@pytest.fixture(scope="module")
def coll():
    return NumpyCollection.load(INDEX_DIR)


def _retrieve(coll, query, **kw):
    return retriever.retrieve(query, collection=coll, embed_fn=local_embed.embed_query, **kw)


# ── Scheme-specific retrieval picks the right scheme (E-3.x, SC1) ──────────
@pytest.mark.parametrize(
    "query,expected_slug",
    [
        ("riskometer of HDFC Mid Cap Fund", "hdfc-mid-cap-fund"),
        ("exit load of HDFC Small Cap Fund", "hdfc-small-cap-fund"),
        ("benchmark of HDFC Large Cap Fund", "hdfc-large-cap-fund"),
        ("who manages HDFC Flexi Cap Fund", "hdfc-equity-fund"),
    ],
)
def test_scheme_specific_retrieval(coll, query, expected_slug):
    # Mirror the real pipeline: the classifier's scheme_hint filters retrieval
    # to that scheme's chunks (KIM/SID hub chunks have no scheme_name).
    scheme_hint = corpus.resolve_scheme(query)
    r = _retrieve(coll, query, scheme_hint=scheme_hint)
    assert r.has_match, f"no match for {query!r}"
    assert expected_slug in (r.citation or ""), f"{query!r} cited {r.citation}"


# ── CAS / capital-gains process content is now retrievable (SC12) ─────────
@pytest.mark.parametrize(
    "query",
    [
        "how do I download a consolidated account statement",
        "how to get a capital gains statement for mutual funds",
    ],
)
def test_statement_process_retrieval(coll, query):
    r = _retrieve(coll, query)
    assert r.has_match
    assert "hdfcfund.com" in (r.citation or "")


# ── General MF concept retrieves AMFI/SEBI education (SC13) ────────────────
def test_general_concept_retrieval(coll):
    r = _retrieve(coll, "what is a mutual fund")
    assert r.has_match
    assert any(host in (r.citation or "") for host in ("amfiindia.com", "sebi.gov.in", "groww.in"))


# ── Off-corpus query falls below threshold → no match (SC14, RET-2) ───────
@pytest.mark.parametrize(
    "query",
    [
        "what is the capital of France",
        "who won the football world cup in 2018",
    ],
)
def test_off_corpus_below_threshold(coll, query):
    r = _retrieve(coll, query)
    assert r.has_match is False, f"off-topic query unexpectedly matched (score={r.best_score:.3f})"
