"""Compiler-free embeddings via fastembed (ONNX) — LOCAL VERIFICATION BACKEND.

Uses BAAI/bge-small-en-v1.5 (384-dim, normalized) through fastembed, which needs
no PyTorch and ships Python-3.13 wheels. Same model is used for both ingestion
and query embeddings here, preserving vector-space consistency (D-29).

Production default remains sentence-transformers/all-MiniLM-L6-v2 (D-3); this
fallback exists only because the torch/Chroma stack won't build on this machine.
"""

from __future__ import annotations

from typing import Iterable

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding  # local import

        _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    model = _get_model()
    return [vec.tolist() for vec in model.embed(list(texts))]


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
