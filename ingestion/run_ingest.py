"""Ingestion orchestrator (Docs/implementation-plan.md Phase 2).

Pipeline per source: fetch -> clean -> extract -> chunk/tag -> embed -> upsert.
- Stamps a single ISO ``scrape_date`` for the whole run (freshness; D-26).
- Idempotent: clears the collection first so a rebuild replaces the prior index.
- Per-source failures are logged and skipped; the rest of the index still builds
  (edge ING-8).

Run:  python -m ingestion.run_ingest
      python -m ingestion.run_ingest --no-cache    (force re-fetch)

This module belongs to the OFFLINE ingestion plane and does NOT import backend/
(decision D-6). It reads its own env via dotenv.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ingestion import clean as cleaner
from ingestion import extract as extractor
from ingestion import scrape
from ingestion.chunk_embed import Chunk, make_chunks, upsert_chunks

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
SOURCES_PATH: Path = ROOT_DIR / "data" / "sources.json"

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s")
log = logging.getLogger("ingest")


def _load_sources() -> list[dict[str, Any]]:
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def _env(name: str, default: str) -> str:
    val = os.environ.get(name, default)
    return val if val and val.strip() else default


def build_chunks_for_source(source: dict[str, Any], scrape_date: str, *, use_cache: bool) -> list[Chunk]:
    """Fetch + clean + extract + chunk one source. Raises on fetch failure."""
    raw = scrape.fetch(source, use_cache=use_cache)
    text = cleaner.clean(raw.content, is_text_extracted=raw.is_text_extracted)
    fields = extractor.extract_fields(text)
    summary = extractor.facts_summary(fields, source.get("scheme_name"))
    return make_chunks(text, source, scrape_date, prefix=summary)


def run(*, use_cache: bool = True) -> dict[str, Any]:
    """Run the full ingestion. Returns a summary dict."""
    load_dotenv()
    chroma_dir = _env("CHROMA_DIR", str(ROOT_DIR / "data" / "chroma"))
    collection = _env("CHROMA_COLLECTION", "mf_faq")
    model_name = _env("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    scrape_date = date.today().isoformat()

    sources = _load_sources()
    log.info("Ingesting %d sources (scrape_date=%s)", len(sources), scrape_date)

    # Idempotent rebuild: drop the existing collection first (D-26).
    try:
        import chromadb  # local import

        client = chromadb.PersistentClient(path=chroma_dir)
        try:
            client.delete_collection(collection)
            log.info("Cleared existing collection %r", collection)
        except Exception:  # noqa: BLE001 - first run: nothing to delete
            pass
    except Exception as exc:  # noqa: BLE001
        log.error("Could not initialize Chroma at %s: %s", chroma_dir, exc)
        raise

    all_chunks: list[Chunk] = []
    skipped: list[str] = []
    per_source: dict[str, int] = {}

    for source in sources:
        sid = source["id"]
        try:
            chunks = build_chunks_for_source(source, scrape_date, use_cache=use_cache)
            if not chunks:
                log.warning("No chunks produced for %s (%s)", sid, source["url"])
                skipped.append(sid)
                continue
            all_chunks.extend(chunks)
            per_source[sid] = len(chunks)
            log.info("  %-26s -> %3d chunks", sid, len(chunks))
        except scrape.FetchError as exc:
            log.error("  SKIP %s: %s", sid, exc)
            skipped.append(sid)
        except Exception as exc:  # noqa: BLE001 - keep going (ING-8)
            log.error("  SKIP %s (unexpected): %s", sid, exc)
            skipped.append(sid)

    written = upsert_chunks(
        all_chunks, chroma_dir=chroma_dir, collection_name=collection, model_name=model_name
    )

    summary = {
        "scrape_date": scrape_date,
        "sources_total": len(sources),
        "sources_ingested": len(per_source),
        "sources_skipped": skipped,
        "chunks_written": written,
        "per_source": per_source,
        "chroma_dir": chroma_dir,
        "collection": collection,
    }
    log.info(
        "Done: %d/%d sources, %d chunks. Skipped: %s",
        len(per_source), len(sources), written, skipped or "none",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the 20-URL corpus into ChromaDB.")
    parser.add_argument("--no-cache", action="store_true", help="Force re-fetch (ignore raw_cache).")
    args = parser.parse_args()
    run(use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
