"""Threshold-tuning harness (Phase 3 / eval E-3.8).

Runs a set of in-corpus ("present") and out-of-corpus ("absent") queries against
the live Chroma index and prints the best similarity score for each. Use the
separation between the two groups to choose SCORE_THRESHOLD in .env.

Requires a populated index (run `python -m ingestion.run_ingest` first) and the
heavy deps installed. Run:  python -m backend.rag.tune_threshold
"""

from __future__ import annotations

from backend.rag import retriever

# One representative query per factual type (should clear the threshold).
PRESENT_QUERIES: list[str] = [
    "What is the expense ratio of HDFC Mid Cap Fund?",
    "Exit load for HDFC Small Cap Fund?",
    "Minimum SIP amount for HDFC Large Cap Fund?",
    "Minimum investment in HDFC Flexi Cap Fund?",
    "Riskometer of HDFC Gold ETF Fund of Fund?",
    "What is the benchmark for HDFC Mid Cap Fund?",
    "Who manages HDFC ELSS Tax Saver?",
    "Experience of the fund manager of HDFC Mid Cap Fund?",
    "Tax rules for HDFC Small Cap Fund?",
    "Lock-in period for HDFC ELSS Tax Saver?",
    "How much tax deduction can I claim with ELSS?",
    "How to download capital gains statement?",
    "How to get consolidated account statement?",
    "Fund size of HDFC Large Cap Fund?",
    "What SEBI category is HDFC Flexi Cap Fund?",
    "What is a mutual fund?",
    "What does the riskometer mean?",
]

# Queries whose answer is NOT in the corpus (should fall BELOW the threshold).
ABSENT_QUERIES: list[str] = [
    "What is the expense ratio of HDFC Balanced Advantage Fund?",
    "SBI Small Cap Fund expense ratio?",
    "What is the capital of France?",
    "Parag Parikh Flexi Cap NAV?",
    "How do I cook biryani?",
]


def _best(query: str) -> float:
    # Use a very low threshold so we always get the raw best score back.
    result = retriever.retrieve(query, threshold=-1.0)
    return result.best_score


def main() -> None:
    print("\n=== PRESENT (in-corpus) — want HIGH scores ===")
    present_scores = []
    for q in PRESENT_QUERIES:
        s = _best(q)
        present_scores.append(s)
        print(f"  {s:6.3f}  {q}")

    print("\n=== ABSENT (out-of-corpus) — want LOW scores ===")
    absent_scores = []
    for q in ABSENT_QUERIES:
        s = _best(q)
        absent_scores.append(s)
        print(f"  {s:6.3f}  {q}")

    if present_scores and absent_scores:
        min_present = min(present_scores)
        max_absent = max(absent_scores)
        print("\n--- Summary ---")
        print(f"  min(present) = {min_present:.3f}")
        print(f"  max(absent)  = {max_absent:.3f}")
        if min_present > max_absent:
            suggested = round((min_present + max_absent) / 2, 3)
            print(f"  Clean separation. Suggested SCORE_THRESHOLD = {suggested}")
        else:
            print("  Overlap detected — review chunking/queries; pick a threshold")
            print("  that maximizes present-pass while minimizing absent-pass.")


if __name__ == "__main__":
    main()
