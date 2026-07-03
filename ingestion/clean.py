"""Clean + normalize fetched content (Docs/data-flow-architecture.md §3).

- Strip nav/ads/scripts/boilerplate from HTML.
- Normalize whitespace and Unicode (NFKC) while preserving ₹ and % (edge ING-5).

``normalize_text`` is a pure function (offline-testable). ``clean_html`` needs
BeautifulSoup, imported locally so this module imports without it.
"""

from __future__ import annotations

import re
import unicodedata

# Tags whose contents are boilerplate / non-content.
_STRIP_TAGS = ("script", "style", "noscript", "nav", "footer", "header", "aside", "svg", "form")

_WHITESPACE_RE = re.compile(r"[ \t\u00a0]+")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """Normalize Unicode + whitespace, preserving ₹ and %.

    - NFKC normalization (fixes mojibake / fullwidth chars) but we keep ₹ (U+20B9).
    - Collapse runs of spaces/tabs/nbsp to a single space.
    - Collapse 3+ blank lines to a double newline.
    - Trim trailing spaces per line.
    """
    if not text:
        return ""

    # NFKC can decompose some symbols; protect the rupee sign explicitly.
    text = text.replace("\u20b9", "₹")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u20b9", "₹")  # re-assert after NFKC

    # Common HTML entities that may survive extraction.
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&rsquo;", "'")
        .replace("&ldquo;", '"')
        .replace("&rdquo;", '"')
    )

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Trim each line, collapse intra-line whitespace.
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _MULTINEWLINE_RE.sub("\n\n", text)
    return text.strip()


def clean_html(html: str) -> str:
    """Strip boilerplate tags and return normalized visible text."""
    from bs4 import BeautifulSoup  # local import

    soup = BeautifulSoup(html, "html.parser")
    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    text = soup.get_text(separator="\n")
    return normalize_text(text)


def clean(raw_content: str, *, is_text_extracted: bool) -> str:
    """Entry point: clean HTML or normalize already-extracted PDF text."""
    if is_text_extracted:
        return normalize_text(raw_content)
    return clean_html(raw_content)
