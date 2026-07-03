"""Retrieval core — read-path against the persisted Chroma index (Phase 3).

Given a query, embed it (same model as ingestion — D-29), run a top-k similarity
search with a score threshold, optionally pre-filter by scheme/data_type hints,
and select the single citation (source_type priority tie-break, D-21).

Below-threshold → ``has_match = False`` so the caller returns "I don't have this
in my sources" (anti-hallucination, SC14 / edge RET-2).

Heavy deps (sentence-transformers, chromadb) are lazy-loaded. The pure ranking /
scoring / filtering helpers are import-safe and unit-tested offline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from backend import corpus

log = logging.getLogger("retriever")

# source_type retrieval priority for scheme-specific facts (lower = preferred).
_SOURCE_TYPE_PRIORITY: dict[str, int] = {
    "groww_scheme_page": 0,
    "amc_official": 1,
    "sebi": 2,
    "amfi": 3,
}


@dataclass
class RetrievedChunk:
    """One retrieved chunk with its score and metadata."""

    text: str
    score: float
    source_url: str
    source_type: str
    scheme_name: str
    data_type: str
    scrape_date: str
    chunk_id: str = ""


@dataclass
class RetrievalResult:
    """Outcome of a retrieval call (a value, not an exception — conventions §4.2)."""

    chunks: list[RetrievedChunk] = field(default_factory=list)
    best_score: float = 0.0
    has_match: bool = False
    citation: str | None = None
    scrape_date: str | None = None


# ── Pure helpers (offline-testable) ───────────────────────────────────────
def distance_to_score(distance: float) -> float:
    """Convert Chroma cosine distance to a [0,1]-ish similarity (1 - distance)."""
    return 1.0 - float(distance)


def passes_threshold(best_score: float, threshold: float) -> bool:
    """True iff the best score clears the configured threshold (RET-2)."""
    return best_score >= threshold


def build_where(scheme_hint: str | None, data_type_hint: str | None) -> dict[str, Any] | None:
    """Build a Chroma ``where`` metadata filter from classifier hints (RET-10).

    Uses ``$and`` when both hints are present. Returns None when no hints.
    """
    clauses: list[dict[str, Any]] = []
    if scheme_hint:
        clauses.append({"scheme_name": scheme_hint})
    if data_type_hint:
        clauses.append({"data_type": data_type_hint})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _priority(source_type: str) -> int:
    return _SOURCE_TYPE_PRIORITY.get(source_type, 99)


def rank_and_select_citation(chunks: Sequence[RetrievedChunk]) -> str | None:
    """Pick the citation: highest score, tie-broken by source_type priority (D-21).

    Only returns a URL that is in the corpus allow-list (defensive; INV-6).
    """
    if not chunks:
        return None
    # Sort by score desc, then by source priority asc. Round score to group ties.
    ordered = sorted(chunks, key=lambda c: (-round(c.score, 3), _priority(c.source_type)))
    for c in ordered:
        if corpus.is_allowed_url(c.source_url):
            return c.source_url
    return None


def parse_query_result(result: dict[str, Any]) -> list[RetrievedChunk]:
    """Convert a Chroma ``query`` result dict into RetrievedChunk objects."""
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]
    ids = (result.get("ids") or [[]])[0]

    chunks: list[RetrievedChunk] = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else 1.0
        chunk_id = ids[i] if i < len(ids) else ""
        chunks.append(
            RetrievedChunk(
                text=doc,
                score=distance_to_score(dist),
                source_url=meta.get("source_url", ""),
                source_type=meta.get("source_type", ""),
                scheme_name=meta.get("scheme_name", ""),
                data_type=meta.get("data_type", ""),
                scrape_date=meta.get("scrape_date", ""),
                chunk_id=chunk_id,
            )
        )
    return chunks


def assemble_result(chunks: list[RetrievedChunk], threshold: float) -> RetrievalResult:
    """Build a RetrievalResult from parsed chunks + the threshold gate."""
    if not chunks:
        return RetrievalResult()
    best = max(c.score for c in chunks)
    has = passes_threshold(best, threshold)
    if not has:
        return RetrievalResult(chunks=chunks, best_score=best, has_match=False)
    citation = rank_and_select_citation(chunks)
    # scrape_date from the cited chunk (fallback to the top chunk).
    scrape_date = next(
        (c.scrape_date for c in chunks if c.source_url == citation and c.scrape_date),
        chunks[0].scrape_date,
    )
    return RetrievalResult(
        chunks=chunks,
        best_score=best,
        has_match=True,
        citation=citation,
        scrape_date=scrape_date,
    )


# ── Heavy singletons (lazy) ───────────────────────────────────────────────
# Production path = ChromaDB + sentence-transformers. When those aren't available
# (e.g. Python 3.13, no compiler — D-52), we transparently fall back to the local
# numpy store + fastembed so the app still serves for free. ``_local_mode`` keeps
# the embedder and the store on the SAME backend (vector-space consistency, D-29).
_embedder = None
_collection = None
_local_mode: bool | None = None


def _local_index_dir() -> Path:
    from backend.config import settings

    return Path(settings.chroma_dir).parent / "local_index"


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer  # local import

        from backend.config import settings

        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def _get_collection():
    global _collection, _local_mode
    if _collection is not None:
        return _collection

    # Try the production Chroma path first.
    try:
        import chromadb  # local import

        from backend.config import settings

        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        _collection = client.get_collection(settings.chroma_collection)
        _local_mode = False
        return _collection
    except Exception as exc:  # noqa: BLE001 - fall back to the local numpy index
        from backend.rag.local_store import NumpyCollection

        _collection = NumpyCollection.load(_local_index_dir())  # raises if absent
        _local_mode = True
        log.warning("retriever using local numpy index fallback (%s)", type(exc).__name__)
        return _collection


def _default_embed(query: str) -> list[float]:
    global _local_mode
    if _local_mode is None:
        _get_collection()  # determine which backend is active
    if _local_mode:
        from backend.rag import local_embed  # local import

        return local_embed.embed_query(query)
    embedder = _get_embedder()
    return embedder.encode([query], normalize_embeddings=True)[0].tolist()


class IndexUnavailable(RuntimeError):
    """Raised when the vector index cannot be loaded (SYS-4 → 503)."""


def get_index_info() -> dict[str, Any]:
    """Non-throwing index status for /api/health (E-8.1).

    Returns ``{"loaded": bool, "count": int | None, "error": str | None}``.
    """
    try:
        coll = _get_collection()
        return {"loaded": True, "count": coll.count(), "error": None}
    except Exception as exc:  # noqa: BLE001 - health must never raise
        return {"loaded": False, "count": None, "error": type(exc).__name__}


# ── Public entry point ────────────────────────────────────────────────────
def retrieve(
    query: str,
    *,
    top_k: int | None = None,
    threshold: float | None = None,
    scheme_hint: str | None = None,
    data_type_hint: str | None = None,
    collection: Any | None = None,
    embed_fn: Callable[[str], list[float]] | None = None,
) -> RetrievalResult:
    """Retrieve top-k chunks for ``query`` and decide whether we have a match.

    ``collection`` and ``embed_fn`` can be injected for testing; otherwise the
    lazy Chroma collection + sentence-transformers embedder are used.
    """
    if not query or not query.strip():
        return RetrievalResult()

    # Resolve config defaults lazily (avoids importing settings in offline tests
    # that inject their own collection/embed_fn).
    if top_k is None or threshold is None:
        from backend.config import settings

        top_k = top_k if top_k is not None else settings.top_k
        threshold = threshold if threshold is not None else settings.score_threshold

    embed = embed_fn or _default_embed
    coll = collection if collection is not None else _get_collection()

    query_vec = embed(query)
    where = build_where(scheme_hint, data_type_hint)

    # Try the filtered query first; if it yields nothing, fall back to unfiltered.
    result = coll.query(query_embeddings=[query_vec], n_results=top_k, where=where)
    chunks = parse_query_result(result)
    if not chunks and where is not None:
        result = coll.query(query_embeddings=[query_vec], n_results=top_k)
        chunks = parse_query_result(result)

    return assemble_result(chunks, threshold)
