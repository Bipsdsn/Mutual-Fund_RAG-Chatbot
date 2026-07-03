"""Pydantic request/response models for the API boundary (conventions §1).

The response schema is the unified contract used by every branch
(Docs/data-flow-architecture.md §7.2). Phase 4 populates the FACTUAL and
NO_SOURCE paths; later phases add ADVISORY_REFUSAL / OUT_OF_SCOPE / PII_REJECTED.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ResponseType(str, Enum):
    """Canonical response_type values (conventions §2.3)."""

    FACTUAL = "FACTUAL"
    ADVISORY_REFUSAL = "ADVISORY_REFUSAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NO_SOURCE = "NO_SOURCE"
    PII_REJECTED = "PII_REJECTED"
    ERROR = "ERROR"  # transient service error (e.g. Groq timeout) — never fabricate


class QueryRequest(BaseModel):
    """Inbound query payload: { "query": "<text>" }."""

    query: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    """Unified response for all branches."""

    answer: str
    source_url: str | None = None
    last_updated: str | None = None
    response_type: ResponseType = ResponseType.FACTUAL
    refused: bool = False


class HealthResponse(BaseModel):
    """GET /api/health — service + index status (E-8.1)."""

    status: str  # "ok" when the index is loaded, else "degraded"
    index_loaded: bool
    chunk_count: int | None = None
    detail: str | None = None


class ExamplesResponse(BaseModel):
    """GET /api/examples — exactly 3 starter questions (E-8.3)."""

    examples: list[str]


class MetaResponse(BaseModel):
    """GET /api/meta — freshness + coverage (E-8.4)."""

    schemes: list[str]
    scheme_count: int
    scrape_date: str | None = None
    disclaimer: str = "Facts-only. No investment advice."
