"""Tests for the optional in-app re-ingestion scheduler (D-71).

No real scraping/APScheduler timing — the ingest callable is injected and the
enabled/disabled wiring is checked deterministically.
"""

from __future__ import annotations

from dataclasses import replace

from backend import scheduler
from backend.config import settings


def teardown_function(_):
    # Ensure no scheduler leaks between tests.
    scheduler.shutdown()


# ── Job wrapper: calls the ingest fn and returns its summary ──────────────
def test_job_runs_injected_ingest():
    calls = {"n": 0}

    def fake_ingest():
        calls["n"] += 1
        return {"chunks_written": 42}

    out = scheduler.run_ingestion_job(fake_ingest)
    assert calls["n"] == 1
    assert out == {"chunks_written": 42}


# ── Job wrapper: a failing ingest is swallowed (never crashes the API) ────
def test_job_swallows_errors():
    def boom():
        raise RuntimeError("scrape blew up")

    assert scheduler.run_ingestion_job(boom) is None


# ── Disabled by default → no scheduler starts ─────────────────────────────
def test_disabled_by_default():
    assert settings.scheduler_enabled is False
    sched = scheduler.start_if_enabled(settings)
    assert sched is None


# ── Non-positive interval → not started even if enabled ───────────────────
def test_bad_interval_not_started():
    cfg = replace(settings, scheduler_enabled=True, ingest_interval_hours=0)
    assert scheduler.start_if_enabled(cfg) is None


# ── Enabled → scheduler starts, schedules the job, and stops cleanly ──────
def test_enabled_starts_and_schedules_job():
    ran = {"n": 0}

    def fake_ingest():
        ran["n"] += 1
        return {"chunks_written": 1}

    cfg = replace(
        settings,
        scheduler_enabled=True,
        ingest_interval_hours=24,
        ingest_run_on_start=False,  # don't fire during the test
    )
    sched = scheduler.start_if_enabled(cfg, ingest_fn=fake_ingest)
    # If APScheduler isn't installed, start returns None — skip the rest.
    if sched is None:
        return
    try:
        assert sched.get_job("reingest") is not None
    finally:
        scheduler.shutdown()
    # Confirmed the job is registered; we didn't run it (run_on_start=False).
    assert ran["n"] == 0
