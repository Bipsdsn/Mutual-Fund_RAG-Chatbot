"""Out-of-scope responder (Phase 7).

States the coverage boundary for OUT_OF_SCOPE queries — the 6 covered HDFC
schemes + the AMC link (edge SCO-1..5). No disclaimer footer here; the
Formatter appends it.
"""

from __future__ import annotations

from backend import corpus

# The single link for out-of-scope replies (HDFC AMC, allow-listed).
SCOPE_LINK = corpus.AMC_HOME_URL


def build() -> str:
    """Return the scope-boundary message body (≤3 sentences, no footer)."""
    schemes = "; ".join(corpus.COVERED_SCHEMES)
    return (
        f"I only cover these six HDFC Mutual Fund schemes: {schemes}. "
        "For any other scheme or fund house, please check the official source "
        f"at {corpus.AMC_HOME_URL}"
    )
