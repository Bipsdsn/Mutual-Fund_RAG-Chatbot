"""Build the scraped fact table (data/facts.json) from extracted fields.

Runs during a real ingest: for each scheme source, the fields pulled by
``extract.extract_fields`` are mapped to fact-store entries (value + citation +
scrape_date). Regulatory facts (lock_in, ELSS tax_benefit) are NOT written here
— they are seeded in code (backend/rag/facts.py).

Pure transform (``to_fact_entries``) is offline-testable; ``write_facts`` does
the file IO.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# extract.py field names → fact-store data_type keys (only exact, citable values).
_FIELD_TO_DATA_TYPE: dict[str, str] = {
    "expense_ratio": "expense_ratio",
    "nav": "nav",
    "aum": "aum",
    "min_sip": "sip_details",
    "min_lumpsum": "lumpsum",
}

# Light presentation for values that are bare numbers in the source.
_VALUE_SUFFIX: dict[str, str] = {
    "expense_ratio": "%",
    "aum": " crore",
}
_VALUE_PREFIX: dict[str, str] = {
    "nav": "₹",
    "min_sip": "₹",
    "min_lumpsum": "₹",
}


def to_fact_entries(fields: dict[str, str], *, source_url: str, scrape_date: str) -> dict[str, dict[str, str]]:
    """Map extracted fields to {data_type: {value, source_url, scrape_date}}.

    Only known, citable numeric fields are included; anything else is skipped so
    we never store a half-sentence as an "exact" fact.
    """
    entries: dict[str, dict[str, str]] = {}
    for field_name, raw in fields.items():
        data_type = _FIELD_TO_DATA_TYPE.get(field_name)
        if not data_type or not raw:
            continue
        value = f"{_VALUE_PREFIX.get(field_name, '')}{raw}{_VALUE_SUFFIX.get(field_name, '')}"
        entries[data_type] = {
            "value": value,
            "source_url": source_url,
            "scrape_date": scrape_date,
        }
    return entries


def write_facts(facts_by_scheme: dict[str, dict[str, dict[str, str]]], *, path: str | Path, scrape_date: str) -> int:
    """Write the scraped fact table to ``path``. Returns scheme count written."""
    doc: dict[str, Any] = {
        "generated": scrape_date,
        "note": "Scraped exact facts per scheme; regulatory facts are seeded in code.",
        "facts": facts_by_scheme,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(facts_by_scheme)
