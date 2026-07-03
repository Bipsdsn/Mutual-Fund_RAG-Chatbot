"""Best-effort structured field extraction from cleaned scheme text.

These regex heuristics pull common Groww data points (expense ratio, exit load,
SIP, lumpsum, AUM, NAV, lock-in, etc.). Extraction is *best-effort*: a missing
field is simply absent (never fabricated — edge ING-4). Extracted fields are
prepended as a short "facts summary" line so retrieval has clean, dense text.

Pure functions — offline-testable.
"""

from __future__ import annotations

import re

# Regexes are intentionally permissive; they assist retrieval, they do not
# replace the source text (which is always chunked and embedded as-is).
_PATTERNS: dict[str, re.Pattern[str]] = {
    "expense_ratio": re.compile(r"expense\s*ratio[^0-9]{0,20}(\d{1,2}\.\d{1,3})\s*%", re.I),
    "min_sip": re.compile(r"(?:min(?:imum)?\.?\s*)?sip[^₹0-9]{0,20}₹?\s*([\d,]{2,7})", re.I),
    "min_lumpsum": re.compile(r"(?:min(?:imum)?\.?\s*)?(?:lump\s*sum|lumpsum|investment)[^₹0-9]{0,20}₹?\s*([\d,]{2,9})", re.I),
    "aum": re.compile(r"(?:aum|fund\s*size)[^₹0-9]{0,20}₹?\s*([\d,]+(?:\.\d+)?)\s*(?:cr|crore)", re.I),
    "nav": re.compile(r"\bnav\b[^₹0-9]{0,20}₹?\s*([\d,]+\.\d{1,4})", re.I),
    "exit_load": re.compile(r"exit\s*load[^.]{0,120}", re.I),
    "lock_in": re.compile(r"lock[\s-]*in[^.]{0,60}", re.I),
    "stamp_duty": re.compile(r"stamp\s*duty[^.]{0,40}", re.I),
    "benchmark": re.compile(r"benchmark[^.\n]{0,80}", re.I),
    "riskometer": re.compile(r"(very\s*high|moderately\s*high|moderate(?:ly\s*low)?|low\s*to\s*moderate|high|low)\s*risk", re.I),
}


def extract_fields(text: str) -> dict[str, str]:
    """Return a dict of best-effort extracted fields (only those found)."""
    found: dict[str, str] = {}
    if not text:
        return found
    for name, pattern in _PATTERNS.items():
        m = pattern.search(text)
        if m:
            # Use the captured group if present, else the whole match, trimmed.
            value = (m.group(1) if m.groups() else m.group(0)).strip()
            value = re.sub(r"\s+", " ", value)
            if value:
                found[name] = value
    return found


def facts_summary(fields: dict[str, str], scheme_name: str | None) -> str:
    """Render extracted fields as a compact summary line to aid retrieval."""
    if not fields:
        return ""
    prefix = f"{scheme_name}: " if scheme_name else ""
    parts = [f"{k.replace('_', ' ')} = {v}" for k, v in fields.items()]
    return f"{prefix}" + "; ".join(parts)
