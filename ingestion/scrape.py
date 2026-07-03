"""Fetch raw content for a source by its ``fetch_mode`` (Docs/decisions.md D-24).

Modes:
- ``html_static``: requests + BeautifulSoup-ready raw HTML.
- ``html_js``: Playwright rendered DOM (for JS-heavy Groww pages).
- ``pdf``: download + extract text via pdfplumber (pypdf fallback).

Heavy libs (Playwright, pdfplumber) are imported lazily inside the functions so
this module imports cleanly without them installed (offline unit tests).

Respectful fetching: custom User-Agent, timeouts, small delays, graceful failure
(edge cases ING-1, ING-2, ING-8).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
RAW_CACHE_DIR: Path = ROOT_DIR / "data" / "raw_cache"

USER_AGENT = (
    "MF-FAQ-Chatbot/0.1 (educational RAG prototype; contact: project maintainer)"
)
REQUEST_TIMEOUT_S = 30
POLITE_DELAY_S = 1.0


class FetchError(RuntimeError):
    """Raised when a source cannot be fetched. Caller skips + logs (ING-8)."""


@dataclass
class RawDoc:
    """Raw fetched content for one source."""

    source_id: str
    url: str
    fetch_mode: str
    content: str            # raw HTML (html_*) or extracted text (pdf)
    is_text_extracted: bool  # True for pdf (already text), False for html


# ── Cache helpers ─────────────────────────────────────────────────────────
def _cache_path(source_id: str, fetch_mode: str) -> Path:
    ext = "pdf.txt" if fetch_mode == "pdf" else "html"
    return RAW_CACHE_DIR / f"{source_id}.{ext}"


def _read_cache(source_id: str, fetch_mode: str) -> str | None:
    path = _cache_path(source_id, fetch_mode)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return None


def _write_cache(source_id: str, fetch_mode: str, content: str) -> None:
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(source_id, fetch_mode).write_text(content, encoding="utf-8", errors="replace")


# ── Fetchers (heavy imports are local) ────────────────────────────────────
def _fetch_html_static(url: str) -> str:
    import requests  # local import

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_S)
    resp.raise_for_status()
    return resp.text


def _fetch_html_js(url: str) -> str:
    from playwright.sync_api import sync_playwright  # local import

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT_S * 1000)
            # Give client-side rendering a moment to settle.
            page.wait_for_timeout(1500)
            return page.content()
        finally:
            browser.close()


def _fetch_pdf(url: str) -> str:
    import io

    import requests  # local import

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_S)
    resp.raise_for_status()
    data = resp.content

    # Prefer pdfplumber (better tables); fall back to pypdf.
    try:
        import pdfplumber  # local import

        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        text = "\n".join(text_parts)
        if text.strip():
            return text
    except Exception:  # noqa: BLE001 - fall through to pypdf
        pass

    from pypdf import PdfReader  # local import

    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


_FETCHERS = {
    "html_static": _fetch_html_static,
    "html_js": _fetch_html_js,
    "pdf": _fetch_pdf,
}


def fetch(source: dict[str, Any], *, use_cache: bool = True, polite_delay: bool = True) -> RawDoc:
    """Fetch one source. Uses the dev cache when available (decision D-27).

    Raises FetchError on failure so the orchestrator can skip + log (ING-8).
    """
    source_id = source["id"]
    url = source["url"]
    mode = source["fetch_mode"]

    if mode not in _FETCHERS:
        raise FetchError(f"Unknown fetch_mode {mode!r} for {url}")

    if use_cache:
        cached = _read_cache(source_id, mode)
        if cached is not None:
            return RawDoc(source_id, url, mode, cached, is_text_extracted=(mode == "pdf"))

    try:
        if polite_delay:
            time.sleep(POLITE_DELAY_S)
        content = _FETCHERS[mode](url)
    except Exception as exc:  # noqa: BLE001 - normalize to FetchError
        raise FetchError(f"Failed to fetch {url} ({mode}): {exc}") from exc

    if not content or not content.strip():
        raise FetchError(f"Empty content fetched from {url} ({mode})")

    if use_cache:
        _write_cache(source_id, mode, content)

    return RawDoc(source_id, url, mode, content, is_text_extracted=(mode == "pdf"))
