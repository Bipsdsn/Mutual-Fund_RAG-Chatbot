"""Chunk, tag with metadata, embed, and upsert into ChromaDB.

- Chunking uses LangChain's RecursiveCharacterTextSplitter when available, with a
  dependency-free fallback so chunking + metadata tagging are testable offline.
- Embedding (sentence-transformers) and Chroma upsert are lazy-imported.

Metadata schema per chunk (Docs/data-flow-architecture.md §3.3):
  source_url, source_type, scheme_name, scheme_category, data_type,
  scrape_date, chunk_index  (+ id, text).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CHUNK_SIZE = 700        # ~500–800 tokens worth of characters (heuristic)
CHUNK_OVERLAP = 120     # ~80 tokens of overlap

# Closed set of data types (must match Docs/conventions.md §2.5).
VALID_DATA_TYPES = {
    "expense_ratio", "exit_load", "sip_details", "lumpsum", "risk", "benchmark",
    "fund_manager", "tax", "lock_in", "aum", "nav", "sebi_category",
    "statement_guide", "investor_education", "scheme_facts",
}

# Keyword → data_type refinement (first match wins). Falls back to source default.
_DATA_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("expense ratio", "expense_ratio"),
    ("exit load", "exit_load"),
    ("lock-in", "lock_in"),
    ("lock in", "lock_in"),
    ("sip", "sip_details"),
    ("lump sum", "lumpsum"),
    ("lumpsum", "lumpsum"),
    ("riskometer", "risk"),
    ("risk", "risk"),
    ("benchmark", "benchmark"),
    ("fund manager", "fund_manager"),
    ("capital gain", "tax"),
    ("stcg", "tax"),
    ("ltcg", "tax"),
    ("aum", "aum"),
    ("fund size", "aum"),
    ("nav", "nav"),
    ("consolidated account statement", "statement_guide"),
    ("cas", "statement_guide"),
    ("categor", "sebi_category"),
]


@dataclass
class Chunk:
    """A retrievable chunk + its metadata (the core data contract)."""

    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def infer_data_type(text: str, default: str) -> str:
    """Refine data_type from chunk text; fall back to the source's default."""
    low = text.lower()
    for keyword, dtype in _DATA_TYPE_KEYWORDS:
        if keyword in low:
            return dtype
    return default if default in VALID_DATA_TYPES else "scheme_facts"


def build_chunk_metadata(source: dict[str, Any], data_type: str, scrape_date: str, chunk_index: int) -> dict[str, Any]:
    """Assemble the 7-field metadata schema for one chunk."""
    return {
        "source_url": source["url"],
        "source_type": source["source_type"],
        # Chroma metadata cannot hold None → use empty string for general pages.
        "scheme_name": source.get("scheme_name") or "",
        "scheme_category": source.get("scheme_category") or "",
        "data_type": data_type,
        "scrape_date": scrape_date,
        "chunk_index": chunk_index,
    }


def _split_text(text: str) -> list[str]:
    """Split text into overlapping chunks. Prefer LangChain; fall back to local."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter  # local import

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return [c for c in splitter.split_text(text) if c.strip()]
    except Exception:  # noqa: BLE001 - dependency-free fallback
        return _fallback_split(text)


def _fallback_split(text: str) -> list[str]:
    """Simple char-window splitter with overlap (no external deps)."""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = end - CHUNK_OVERLAP
        if start < 0:
            start = 0
    return chunks


def make_chunks(text: str, source: dict[str, Any], scrape_date: str, *, prefix: str = "") -> list[Chunk]:
    """Split cleaned text into tagged Chunk objects.

    ``prefix`` (e.g., the facts_summary line) is prepended to the document text so
    dense facts are embedded alongside body content.
    """
    body = (prefix + "\n\n" + text).strip() if prefix else text
    pieces = _split_text(body)
    default_dt = source.get("default_data_type", "scheme_facts")

    chunks: list[Chunk] = []
    for i, piece in enumerate(pieces):
        dtype = infer_data_type(piece, default_dt)
        meta = build_chunk_metadata(source, dtype, scrape_date, i)
        chunks.append(Chunk(id=f"{source['id']}_{i:04d}", text=piece, metadata=meta))
    return chunks


# ── Embedding + Chroma upsert (heavy, lazy-imported) ──────────────────────
_embedder = None  # module-level singleton (load once; conventions §5)


def _get_embedder(model_name: str):
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer  # local import

        _embedder = SentenceTransformer(model_name)
    return _embedder


def embed_texts(texts: list[str], model_name: str) -> list[list[float]]:
    """Embed a list of texts with the local sentence-transformers model."""
    embedder = _get_embedder(model_name)
    return embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


def upsert_chunks(chunks: list[Chunk], *, chroma_dir: str, collection_name: str, model_name: str) -> int:
    """Embed chunks and upsert them into a persistent Chroma collection.

    Returns the number of chunks written. (Heavy: imports chromadb + ST.)
    """
    import chromadb  # local import

    if not chunks:
        return 0

    client = chromadb.PersistentClient(path=chroma_dir)
    collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    embeddings = embed_texts([c.text for c in chunks], model_name)
    collection.upsert(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        embeddings=embeddings,
        metadatas=[c.metadata for c in chunks],
    )
    return len(chunks)
