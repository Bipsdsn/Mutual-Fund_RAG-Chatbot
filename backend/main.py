"""FastAPI app — thin orchestration only.

Fixed pipeline (conventions §6.1): PII → classify → retrieve → generate →
FORMAT (always last). Every branch returns through the Formatter so the output
contract (≤3 sentences, one corpus citation, footer, no PII) holds everywhere.

Functions are referenced via the imported modules so they can be monkeypatched
in tests without touching Groq or Chroma.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend import corpus, formatter, scheduler
from backend.config import settings
from backend.guardrails import classifier, pii
from backend.models import (
    ExamplesResponse,
    HealthResponse,
    MetaResponse,
    QueryRequest,
    QueryResponse,
)
from backend.rag import facts, generator, retriever
from backend.responders import refusal, scope

logging.basicConfig(level=settings.log_level, format="%(levelname)s %(message)s")
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the optional re-ingestion scheduler on boot; stop it on shutdown."""
    scheduler.start_if_enabled(settings)
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(
    title="Mutual Fund FAQ Assistant — HDFC MF (Groww)",
    description="Facts-only. No investment advice.",
    version="0.8.0",  # Phase 8 + in-app scheduler
    lifespan=lifespan,
)

# CORS restricted to the configured frontend origin(s) (SYS-5, E-8.7). Not
# wide-open: only ALLOWED_ORIGINS may call the API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _to_response(formatted: formatter.Formatted) -> QueryResponse:
    """Map a Formatter result onto the API response model."""
    return QueryResponse(
        answer=formatted.answer,
        source_url=formatted.source_url,
        last_updated=formatted.last_updated,
        response_type=formatted.response_type,
        refused=formatted.refused,
    )


def _latest_scrape_date() -> str | None:
    """Best-effort freshness date for /api/meta (index metadata → facts.json)."""
    # Prefer the built local index metadata if present.
    records = Path(settings.chroma_dir).parent / "local_index" / "records.json"
    try:
        if records.exists():
            metas = json.loads(records.read_text(encoding="utf-8")).get("metadatas", [])
            for m in metas:
                if m.get("scrape_date"):
                    return m["scrape_date"]
    except (json.JSONDecodeError, OSError):
        pass
    # Fall back to the scraped facts file marker.
    try:
        if facts.FACTS_PATH.exists():
            gen = json.loads(facts.FACTS_PATH.read_text(encoding="utf-8")).get("generated")
            if gen and gen != "pending-ingest":
                return gen
    except (json.JSONDecodeError, OSError):
        pass
    return None


# ── Auxiliary read-only endpoints (Phase 8) ───────────────────────────────
@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Service + index status (E-8.1). Never raises."""
    info = retriever.get_index_info()
    return HealthResponse(
        status="ok" if info["loaded"] else "degraded",
        index_loaded=info["loaded"],
        chunk_count=info["count"],
        detail=None if info["loaded"] else f"index unavailable ({info['error']})",
    )


@app.get("/api/examples", response_model=ExamplesResponse)
def examples() -> ExamplesResponse:
    """Three starter questions for the UI (E-8.3)."""
    return ExamplesResponse(
        examples=[
            "What is the expense ratio of HDFC Mid Cap Fund?",
            "What is the lock-in period of HDFC ELSS Tax Saver?",
            "What is a mutual fund?",
        ]
    )


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    """Coverage + freshness metadata (E-8.4)."""
    return MetaResponse(
        schemes=list(corpus.COVERED_SCHEMES),
        scheme_count=len(corpus.COVERED_SCHEMES),
        scrape_date=_latest_scrape_date(),
    )


@app.post("/api/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    """Pipeline order (conventions §6.1): PII → classify → retrieve → generate → FORMAT."""
    # --- Layer 1: PII guard (runs first; short-circuit) ---
    pii_result = pii.scan(req.query)
    if pii_result.has_pii:
        # Log type names only — never the raw query/value (privacy; §4.6).
        log.info("pii_rejected types=%s", pii_result.pii_types)
        return _to_response(formatter.format_pii(pii.PII_REJECTION_MESSAGE))

    # --- Layer 2: query classifier (advisory / out-of-scope / factual) ---
    cls = classifier.classify(req.query)
    # Log routing signal only — never the raw query (privacy; §4.6).
    log.info(
        "classified label=%s reason=%s scheme_hint=%s data_type_hint=%s",
        cls.label.value, cls.reason, cls.scheme_hint, cls.data_type_hint,
    )

    if cls.label is classifier.Label.ADVISORY:
        return _to_response(formatter.format_refusal(refusal.build()))

    if cls.label is classifier.Label.OUT_OF_SCOPE:
        return _to_response(formatter.format_scope(scope.build()))

    # --- FACTUAL: structured-first, then semantic fallback (D-65) ---
    # 1) Exact fact lookup keyed by the classifier's scheme + data_type hints.
    #    Returns a verbatim value + its own citation — no embedding guesswork.
    fact = facts.lookup(cls.scheme_hint, cls.data_type_hint)
    if fact is not None:
        log.info("fact_hit scheme=%s data_type=%s", fact.scheme_name, fact.data_type)
        return _to_response(
            formatter.format_factual(
                facts.render(fact),
                fact.source_url,
                fact.scrape_date,
                max_sentences=settings.max_sentences,
            )
        )

    # 2) Semantic fallback for educational / open questions (scheme hint feeds
    #    the metadata pre-filter). Index-load failure → 503 (SYS-4, E-8.2).
    try:
        result = retriever.retrieve(req.query, scheme_hint=cls.scheme_hint)
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, no stack trace
        log.error("index_unavailable error=%s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="The knowledge index is temporarily unavailable. Please try again shortly.",
        ) from exc

    # Log retrieval signal only — never the raw query (privacy; conventions §4.6).
    log.info("retrieve best_score=%.3f has_match=%s", result.best_score, result.has_match)

    if not result.has_match:
        return _to_response(formatter.format_no_source())

    # Groq timeout/5xx → graceful retry message, never a fabricated answer (E-8.6).
    try:
        draft = generator.generate(req.query, result.chunks)
    except generator.GroqUnavailable as exc:
        log.error("groq_unavailable error=%s", type(exc).__name__)
        return _to_response(formatter.format_error())

    return _to_response(
        formatter.format_factual(
            draft,
            result.citation,
            result.scrape_date,
            max_sentences=settings.max_sentences,
        )
    )
