# Mutual Fund FAQ Assistant — HDFC Mutual Fund

A **facts-only, RAG-based FAQ assistant** for 6 HDFC Mutual Fund schemes. It answers
verifiable questions (expense ratio, lock-in, NAV, exit load, taxes, statements,
general MF concepts) **only from official sources**, with a citation and freshness
date on every answer. It never gives investment advice, opinions, or predictions.

> **Facts-only. No investment advice.**

Built entirely on a **$0 stack** (local embeddings + local vector store + Groq's free
LLM tier).

---

## Overview

The assistant follows a strict, deterministic pipeline so it stays trustworthy:

```
PII guard  →  Classifier  →  Retrieve (structured facts → semantic)  →  Generate  →  Formatter
```

- **PII guard** blocks PAN / Aadhaar / phone / email / account / OTP before anything else — never echoed, never logged.
- **Classifier** routes each query to FACTUAL, ADVISORY (refused), or OUT_OF_SCOPE.
- **Hybrid retrieval** answers known scheme facts from an exact fact table first (verbatim, no LLM guessing), and falls back to semantic search over the official corpus for open/educational questions.
- **Grounded generation** (Groq) answers only from retrieved context, or says "I don't have this in my sources."
- **Formatter** is the single output gate: ≤3 sentences, exactly one citation from the approved source list, a freshness footer, and a final PII scan — on every branch.

## Product Context

Consumer-facing context is **Groww** (a popular Indian investing app), covering
**HDFC Mutual Fund** schemes. Answers cite official sources — Groww scheme pages,
the HDFC AMC (hdfcfund.com) documents, SEBI, and AMFI.

## Schemes Covered (6)

| Scheme | Category | Lock-in |
|---|---|---|
| HDFC Mid Cap Fund — Direct Growth | Equity — Mid Cap | None |
| HDFC Large Cap Fund — Direct Growth | Equity — Large Cap | None |
| HDFC Small Cap Fund — Direct Growth | Equity — Small Cap | None |
| HDFC Flexi Cap Fund — Direct Growth | Equity — Flexi Cap | None |
| HDFC ELSS Tax Saver — Direct Plan Growth | Equity — ELSS (Tax Saver) | 3 years |
| HDFC Gold ETF Fund of Fund — Direct Plan Growth | Commodities — Gold | None |

Scope is **Direct plans, Growth option** only.

## Architecture

```
                ┌─────────────── Offline ingestion (write path) ───────────────┐
 20 official →  scrape → clean → extract → chunk → embed → vector index + facts.json
   URLs          (requests / PDF)                     (fastembed / ST)   (Chroma / numpy)
                └──────────────────────────────────────────────────────────────┘

 User query
    │
    ▼
 [PII guard] ──hit──► PII_REJECTED
    │ clean
    ▼
 [Classifier] ──advisory──► ADVISORY_REFUSAL (+ AMFI link)
    │            ──out-of-scope──► OUT_OF_SCOPE (+ AMC link, 6-scheme list)
    │ factual
    ▼
 [Fact table lookup] ──hit──► exact value + citation (no LLM)
    │ miss
    ▼
 [Semantic retrieve] ──below threshold──► NO_SOURCE ("I don't have this…")
    │ match
    ▼
 [Groq generate] ──► grounded answer
    │
    ▼
 [Formatter] ──► ≤3 sentences · one corpus citation · freshness footer · PII scan
```

**Stack:** FastAPI · local embeddings (`sentence-transformers/all-MiniLM-L6-v2`, or
`fastembed`/BAAI bge-small on Python 3.13) · local vector store (ChromaDB, or a numpy
store fallback) · **Groq** LLM (`llama-3.1-8b-instant`) · React (Vite) frontend.

See `Docs/` for the full design set (`architecture.md`, `data-flow-architecture.md`,
`decisions.md`, `evals.md`, `edgecases.md`, `conventions.md`).

## Setup

**Prerequisites:** Python 3.10+ and a free Groq API key (https://console.groq.com).
Node 18+ only if you want to run the frontend.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env          # then paste your free GROQ_API_KEY
```

**Build the index** (scrape → embed → store; also writes `data/facts.json`):

```bash
# Production stack (Python ≤3.12, ChromaDB + sentence-transformers):
python -m ingestion.run_ingest

# Compiler-free path (e.g. Python 3.13 — numpy store + fastembed):
python -m ingestion.run_ingest_local
```

**Run the backend:**

```bash
uvicorn backend.main:app --reload      # http://localhost:8000
```

**Run the frontend (optional):**

```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

**API:** `POST /api/query {"query": "..."}` · `GET /api/health` · `GET /api/examples` · `GET /api/meta`

## Source List (20 official URLs)

Every answer cites one of these. No third-party/opinion sources are ever used.

**Groww scheme pages (6)**
1. HDFC Mid Cap — https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
2. HDFC Large Cap — https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
3. HDFC Small Cap — https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
4. HDFC Flexi Cap — https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
5. HDFC ELSS Tax Saver — https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
6. HDFC Gold ETF FoF — https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth

**HDFC AMC — hdfcfund.com (8)**
7. Factsheets — https://www.hdfcfund.com/mutual-funds/factsheets
8. KIM documents — https://www.hdfcfund.com/mutual-funds/fund-documents/kim
9. Offer documents (SID/SAI) — https://www.hdfcfund.com/statutory-disclosure/offer-document-disclosures
10. ELSS official page — https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver/direct
11. Capital gains statement guide — https://www.hdfcfund.com/learn/blog/how-get-capital-gain-statement-mutual-fund-schemes-india
12. Consolidated Account Statement (CAS) — https://www.hdfcfund.com/services/consolidated-account-statement
13. CAS FAQ — https://www.hdfcfund.com/services/faqs/consolidated-account-statement
14. Subscription FAQ — https://www.hdfcfund.com/services/faqs/subscription-related-faqs

**SEBI (3)**
15. Riskometer — https://investor.sebi.gov.in/riskometer.html
16. Understanding Mutual Funds — https://investor.sebi.gov.in/understanding_mf.html
17. Groww blog: guide to SEBI categories — https://groww.in/blog/guide-to-sebi-new-categories-of-mutual-fund

**AMFI (3)**
18. Investor section — https://www.amfiindia.com/investor
19. Types of MF schemes — https://www.amfiindia.com/investor/knowledge-center-info?zoneName=TypesOfMutualFundSchemes
20. Myths & Facts (investor FAQ) — https://www.amfiindia.com/investor/knowledge-center-info?zoneName=MythsAndFactsAboutMutualFunds

## Sample Q&A

Verified live end-to-end (full matrix in `Docs/qa_matrix.md`). Each answer carries a source + freshness footer.

| Question | Answer | Source |
|---|---|---|
| What is the expense ratio of HDFC Mid Cap Fund? | The expense ratio of HDFC Mid Cap Fund is 0.75%. | groww.in |
| What is the lock-in period of HDFC ELSS Tax Saver? | The lock-in period of HDFC ELSS Tax Saver is 3 years. | groww.in |
| How much tax deduction does HDFC ELSS give under 80C? | Investing in HDFC ELSS Tax Saver qualifies for a tax deduction of up to ₹1.5 lakh under Section 80C. | hdfcfund.com |
| What is the lock-in period of HDFC Mid Cap Fund? | HDFC Mid Cap Fund has no lock-in period. | groww.in |
| What is a mutual fund? | A mutual fund is a trust that pools money from investors and invests it in different securities, managed by professional fund managers. | investor.sebi.gov.in |
| How do I download a consolidated account statement? | Visit the HDFC MF website and use "Download Consolidated Account Statement", or request it via email. | hdfcfund.com |
| How do I get a capital gains statement? | You can get it from RTAs like CAMS/KFintech using your PAN and registered email, among other options. | hdfcfund.com |
| Should I invest in HDFC Mid Cap Fund? | *(refused)* I can only share factual information — not investment advice. For investor education, visit AMFI. | amfiindia.com |
| What is the expense ratio of SBI Small Cap Fund? | *(out of scope)* I only cover these six HDFC schemes… | hdfcfund.com |
| My PAN is ABCDE1234F… | *(rejected)* I cannot process requests containing personal information… | — |

## Disclaimer

**Facts-only. No investment advice.** This assistant provides factual information about
mutual fund schemes from official sources only. It does not offer investment advice,
recommendations, opinions, or predictions. Data reflects what the source published on
the scrape date shown in each answer's footer and may change. Consult a SEBI-registered
adviser for investment decisions.

## Known Limitations

- **Data freshness:** market values (NAV, AUM) change; answers show the scrape date and require re-ingestion to refresh.
- **Direct-Growth only:** Regular/IDCW plan figures are out of scope.
- **6 schemes only:** other HDFC schemes and other fund houses return an out-of-scope response.
- **English only** in v1.
- **Anti-bot pages:** hdfcfund.com's portal blocks automated fetches; its documents are ingested from the official CDN PDFs / saved pages.
- **Python 3.13:** the production ChromaDB + sentence-transformers stack needs a C++ compiler; a compiler-free numpy + fastembed backend is used as a $0 fallback (see `Docs/decisions.md` D-52).
- **LLM phrasing:** grounded generation can occasionally be terse; citations and freshness are derived from metadata, never from the model.

## Testing

```bash
python -m pytest -q            # 148 tests (unit + real-index integration)
python -m scripts.qa_matrix    # live end-to-end Q&A matrix (uses Groq)
```

## License / Attribution

Educational prototype. Content belongs to the respective official sources (Groww, HDFC
Mutual Fund, SEBI, AMFI). The assistant links back to these sources on every answer.
