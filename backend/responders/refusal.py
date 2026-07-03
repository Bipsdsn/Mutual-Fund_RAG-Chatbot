"""Advisory refusal responder (Phase 7).

Produces the polite, facts-only refusal body for ADVISORY queries (SC2/SC4,
edge ADV-1..10). It contains an educational link (AMFI, from the corpus
allow-list) but NOT the disclaimer footer — the Formatter appends that
unconditionally so every branch ends the same way.
"""

from __future__ import annotations

from backend import corpus

# The single citation/link for refusals (AMFI investor education, allow-listed).
REFUSAL_LINK = corpus.EDUCATIONAL_URL


def build() -> str:
    """Return the refusal message body (≤3 sentences, no footer)."""
    return (
        "I can only share factual information about HDFC Mutual Fund schemes — "
        "not investment advice, opinions, predictions, or return projections. "
        f"For investor education, visit {REFUSAL_LINK}"
    )
