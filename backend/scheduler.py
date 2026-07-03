"""In-app periodic re-ingestion scheduler (optional; OFF by default).

Runs the ingestion pipeline on a fixed interval so the index/facts refresh
without manual intervention (D-71). Deliberately opt-in via ``SCHEDULER_ENABLED``
because free hosts sleep when idle and frequent scraping risks anti-bot blocks —
so this only makes sense on an always-on deployment.

Design notes:
- APScheduler + the ingestion pipeline are lazy-imported, so importing this
  module (and the app) never drags in the heavy scrape/ML stack or requires the
  scheduler dependency to be installed.
- The job is fully guarded: any failure is logged and swallowed so a bad scrape
  never crashes the API. ``coalesce=True`` + ``max_instances=1`` prevent overlap.
- The ingest callable is injectable for deterministic tests (no real scraping).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from backend.config import Settings

log = logging.getLogger("scheduler")

# Module-level handle to the running scheduler (None when disabled/stopped).
_scheduler: Any | None = None


def _default_ingest() -> dict[str, Any]:
    """Run the real ingestion (lazy import keeps heavy deps out of app import)."""
    from ingestion.run_ingest import run  # local import

    # Force a fresh fetch on scheduled runs so data actually refreshes.
    return run(use_cache=False)


def run_ingestion_job(ingest_fn: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Execute one ingestion run. Never raises — logs and returns None on error."""
    fn = ingest_fn or _default_ingest
    try:
        summary = fn()
        written = (summary or {}).get("chunks_written")
        log.info("scheduled_ingest_ok chunks_written=%s", written)
        return summary
    except Exception as exc:  # noqa: BLE001 - a bad scrape must not crash the API
        log.error("scheduled_ingest_failed error=%s", type(exc).__name__)
        return None


def start_if_enabled(
    settings: Settings,
    *,
    ingest_fn: Callable[[], dict[str, Any]] | None = None,
) -> Any | None:
    """Start the background scheduler when enabled; otherwise no-op.

    Returns the scheduler instance (or None). Safe to call once at startup.
    """
    global _scheduler

    if not settings.scheduler_enabled:
        log.info("scheduler disabled (SCHEDULER_ENABLED not set)")
        return None

    interval = settings.ingest_interval_hours
    if interval <= 0:
        log.warning("scheduler enabled but INGEST_INTERVAL_HOURS<=0; not starting")
        return None

    try:
        from apscheduler.schedulers.background import BackgroundScheduler  # local import
        from apscheduler.triggers.interval import IntervalTrigger  # local import
    except Exception as exc:  # noqa: BLE001 - dependency missing → degrade gracefully
        log.warning("APScheduler unavailable (%s); scheduler not started", type(exc).__name__)
        return None

    if _scheduler is not None:
        return _scheduler

    first_run = (
        datetime.now()
        if settings.ingest_run_on_start
        else datetime.now() + timedelta(hours=interval)
    )

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        lambda: run_ingestion_job(ingest_fn),
        trigger=IntervalTrigger(hours=interval),
        id="reingest",
        next_run_time=first_run,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    log.info(
        "scheduler started interval_hours=%d run_on_start=%s",
        interval, settings.ingest_run_on_start,
    )
    return scheduler


def shutdown() -> None:
    """Stop the scheduler if running (idempotent)."""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception as exc:  # noqa: BLE001
            log.warning("scheduler shutdown error=%s", type(exc).__name__)
        finally:
            _scheduler = None
