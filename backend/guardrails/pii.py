"""Layer 1 — PII Guard (Phase 5).

Deterministic regex gate that runs FIRST in the pipeline (conventions §6.1).
On any match: reject immediately, return the standard message, and report only
the PII *type names* — never the matched values (no echo, no store, no log;
SC5 / edge PII-1..11).

Account-number and OTP detection are context-gated by keywords so legitimate
AUM/NAV figures in a question are not blocked (edge PII-7, decision D-12).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Standard rejection message (Problem Statement §5.4 / context.md §6.4).
PII_REJECTION_MESSAGE = (
    "I cannot process requests containing personal information (PAN, Aadhaar, "
    "phone numbers, email addresses, or account numbers). Please rephrase your "
    "question without personal details.\n\nFacts-only. No investment advice."
)

# --- Always-on detectors ---
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
_AADHAAR_RE = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_PHONE_RE = re.compile(r"\b[6-9]\d{9}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# --- Context-gated detectors (avoid AUM/NAV false positives) ---
_ACCOUNT_NUM_RE = re.compile(r"\b\d{8,18}\b")
_ACCOUNT_CTX_RE = re.compile(r"\b(account|acct|a/?c|a\.c\.?)\b", re.IGNORECASE)
_OTP_NUM_RE = re.compile(r"\b\d{4,6}\b")
_OTP_CTX_RE = re.compile(r"\b(otp|one[\s-]?time\s*password|verification\s*code|passcode)\b", re.IGNORECASE)


@dataclass
class PIIResult:
    """Result of a PII scan. ``pii_types`` holds NAMES ONLY, never values."""

    has_pii: bool = False
    pii_types: list[str] = field(default_factory=list)


def scan(text: str) -> PIIResult:
    """Scan input for PII. Returns type names only (never the matched strings)."""
    if not text:
        return PIIResult()

    found: list[str] = []

    if _PAN_RE.search(text):
        found.append("PAN")
    if _AADHAAR_RE.search(text):
        found.append("AADHAAR")
    if _PHONE_RE.search(text):
        found.append("PHONE")
    if _EMAIL_RE.search(text):
        found.append("EMAIL")

    # Account number only counts in an account context (PII-7).
    if _ACCOUNT_CTX_RE.search(text) and _ACCOUNT_NUM_RE.search(text):
        found.append("ACCOUNT_NUMBER")
    # OTP only counts in an OTP context.
    if _OTP_CTX_RE.search(text) and _OTP_NUM_RE.search(text):
        found.append("OTP")

    return PIIResult(has_pii=bool(found), pii_types=found)
