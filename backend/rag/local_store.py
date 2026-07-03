"""Compiler-free numpy vector store — LOCAL VERIFICATION BACKEND ONLY.

Mimics the subset of the Chroma collection API that ``retriever.retrieve`` uses
(``query(query_embeddings, n_results, where)`` returning ids/documents/
metadatas/distances), so the retriever needs no changes.

Why this exists: ChromaDB's native ``hnswlib`` has no Python-3.13 wheel and needs
a C++ compiler to build, which blocks the committed Chroma path on this machine.
This numpy store is a $0, dependency-light fallback for local end-to-end checks.
Production default remains ChromaDB (decisions.md D-4 / D-52).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def _matches_where(meta: dict[str, Any], where: dict[str, Any] | None) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_matches_where(meta, clause) for clause in where["$and"])
    return all(meta.get(k) == v for k, v in where.items())


class NumpyCollection:
    """Tiny in-memory cosine store with disk persistence."""

    def __init__(self) -> None:
        self.ids: list[str] = []
        self.documents: list[str] = []
        self.metadatas: list[dict[str, Any]] = []
        self.embeddings: np.ndarray = np.zeros((0, 0), dtype=np.float32)

    # --- write ---
    def add(self, ids, documents, embeddings, metadatas) -> None:
        vecs = np.asarray(embeddings, dtype=np.float32)
        # L2-normalize so dot product == cosine similarity.
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vecs = vecs / norms
        if self.embeddings.size == 0:
            self.embeddings = vecs
        else:
            self.embeddings = np.vstack([self.embeddings, vecs])
        self.ids.extend(ids)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)

    # --- read (Chroma-compatible) ---
    def query(self, query_embeddings, n_results: int, where: dict[str, Any] | None = None) -> dict[str, Any]:
        q = np.asarray(query_embeddings[0], dtype=np.float32)
        qn = np.linalg.norm(q) or 1.0
        q = q / qn

        # Candidate indices honoring the where-filter.
        idxs = [i for i, m in enumerate(self.metadatas) if _matches_where(m, where)]
        if not idxs or self.embeddings.size == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        sims = self.embeddings[idxs] @ q  # cosine similarity
        order = np.argsort(-sims)[:n_results]
        sel = [idxs[j] for j in order]

        return {
            "ids": [[self.ids[i] for i in sel]],
            "documents": [[self.documents[i] for i in sel]],
            "metadatas": [[self.metadatas[i] for i in sel]],
            "distances": [[float(1.0 - sims[list(order)[k]]) for k in range(len(sel))]],
        }

    # --- persistence ---
    def save(self, directory: str | Path) -> None:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        np.save(d / "embeddings.npy", self.embeddings)
        (d / "records.json").write_text(
            json.dumps({"ids": self.ids, "documents": self.documents, "metadatas": self.metadatas}),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: str | Path) -> "NumpyCollection":
        d = Path(directory)
        coll = cls()
        coll.embeddings = np.load(d / "embeddings.npy")
        rec = json.loads((d / "records.json").read_text(encoding="utf-8"))
        coll.ids = rec["ids"]
        coll.documents = rec["documents"]
        coll.metadatas = rec["metadatas"]
        return coll

    def count(self) -> int:
        return len(self.ids)
