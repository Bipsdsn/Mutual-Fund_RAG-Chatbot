# Context: RAG-Based Mutual Fund FAQ Chatbot

> Consolidated context document derived from `Problem Statement — MF FAQ Chatbot.md`
> Use this as the single source of truth when building, reviewing, or scoping the project.

---

## 1. Project Snapshot

| Attribute | Value |
|-----------|-------|
| **Project** | RAG-based, facts-only FAQ assistant for mutual fund schemes |
| **Product Context** | Groww (locked-in for ALL subsequent milestones) |
| **Selected AMC** | HDFC Mutual Fund ([hdfcfund.com](http://www.hdfcfund.com)) |
| **Corpus** | 20 official public URLs (Groww + AMC + SEBI + AMFI) |
| **Deadline** | June 26, 2026 — 11:59 PM IST |
| **Submission** | Data architecture + Frontend + Backend + working product + GitHub pushing-Which user will do not AI |
| **Doc Version** | 4.0 (Final — 100% Assignment Coverage), created June 23, 2026 |

### Core Principle
Build a trustworthy, transparent, and compliant MF FAQ assistant that prioritizes **accuracy over intelligence**. Users receive only verified, source-backed information — no advisory bias or speculation.

---

## 2. Problem Context & Rationale

### User Pain Point
Retail investors struggle to find accurate, factual scheme details (expense ratios, exit loads, minimum SIP, lock-in, riskometer, benchmarks, fund managers, statement/tax-doc downloads). These are objective, source-verifiable facts scattered across AMC sites, factsheets, KIMs, SIDs, SEBI circulars, AMFI portals, and Groww pages.

Current workarounds: manual digging through pages/PDFs, AMC helplines, unreliable forums, or generic fintech FAQs.

### Target Users
| Audience | Use Case |
|----------|----------|
| Retail investors | Compare schemes before investing — need quick, sourced facts |
| Customer support teams | Handle repetitive factual MF queries without manual lookup |
| Content teams | Validate scheme details for articles/comparisons |

### What This Is NOT
- ❌ Investment advisor ("Should I buy X?")
- ❌ Returns calculator / performance comparator
- ❌ Portfolio manager or rebalancer
- ❌ KYC/account management tool
- ❌ General financial chatbot

---

## 3. Objectives

1. Answer factual queries about **6 HDFC MF schemes** (5 equity categories + 1 commodity)
2. Use a curated corpus of **20 official public URLs**
3. Provide concise, source-backed responses (**≤3 sentences + one citation + last-updated date**)
4. Refuse advisory/opinion queries politely with an educational link
5. Guard against PII — never accept or store personal data
6. Handle fund management queries (manager name, tenure, education, experience)
7. Handle document access queries (statements, CAS, capital gains reports)

---

## 4. Scheme Coverage (6 Schemes)

| Category | Scheme | Risk / Notes |
|----------|--------|--------------|
| Equity — Large Cap | HDFC Large Cap Fund | Low-to-moderate risk |
| Equity — Mid Cap | HDFC Mid Cap Fund | Moderate risk |
| Equity — Small Cap | HDFC Small Cap Fund | High risk |
| Equity — Flexi Cap | HDFC Flexi Cap Fund | Multi-cap flexibility |
| Equity — ELSS (Tax Saver) | HDFC ELSS Tax Saver | 3-year lock-in; Section 80C |
| Commodities — Gold | HDFC Gold ETF FoF | Non-equity; Fund-of-Funds |

Coverage ensures: all suggested equity categories + one non-equity (Gold), testable lock-in (ELSS = 3 yrs), varied risk levels, and varied structures (direct equity, FoF, tax-saver).

---

## 5. Corpus: 20 Official Public URLs

### A. Groww Scheme Pages (6) — Primary scheme fact source
| # | Scheme | Category | URL |
|---|--------|----------|-----|
| 1 | HDFC Mid Cap Fund Direct Growth | Equity — Mid Cap | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| 2 | HDFC Large Cap Fund Direct Growth | Equity — Large Cap | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 3 | HDFC Small Cap Fund Direct Growth | Equity — Small Cap | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 4 | HDFC Flexi Cap Fund Direct Growth | Equity — Flexi Cap | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 5 | HDFC ELSS Tax Saver Fund Direct Plan Growth | Equity — ELSS | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| 6 | HDFC Gold ETF Fund of Fund Direct Plan Growth | Commodities — Gold | https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth |

### B. HDFC MF Official (AMC) Pages (8) — Factsheets, KIM, SID, FAQs, statement guides
| # | Page | Purpose | URL |
|---|------|---------|-----|
| 7 | Factsheets Portal | Monthly factsheets | https://www.hdfcfund.com/mutual-funds/factsheets |
| 8 | KIM Documents | Key Information Memorandum | https://www.hdfcfund.com/mutual-funds/fund-documents/kim |
| 9 | Offer Documents (SID/SAI) | Scheme Information Documents | https://www.hdfcfund.com/statutory-disclosure/offer-document-disclosures |
| 10 | ELSS Tax Saver Official Page | Lock-in, tax benefits | https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver/direct |
| 11 | Capital Gains Statement Guide | Download capital gains report | https://www.hdfcfund.com/learn/blog/how-get-capital-gain-statement-mutual-fund-schemes-india |
| 12 | Download CAS | CAS download process | https://www.hdfcfund.com/services/consolidated-account-statement |
| 13 | CAS FAQ | CAS frequently asked questions | https://www.hdfcfund.com/services/faqs/consolidated-account-statement |
| 14 | Subscription-Related FAQs | KYC, SID, KIM, investment process | https://www.hdfcfund.com/services/faqs/subscription-related-faqs |

### C. SEBI Official Pages (3) — Regulatory, riskometer, categorization
| # | Page | Purpose | URL |
|---|------|---------|-----|
| 15 | Riskometer Guide | Understanding risk levels | https://investor.sebi.gov.in/riskometer.html |
| 16 | MF Categorization Circular | Scheme categorization rules | https://www.sebi.gov.in/legal/circulars/oct-2017/categorization-and-rationalization-of-the-schemes-offered-by-mutual-funds_36199.html |
| 17 | Groww Blog: SEBI Categories | SEBI categorization explained | https://groww.in/blog/guide-to-sebi-new-categories-of-mutual-fund |

### D. AMFI Official Pages (3) — Investor education
| # | Page | Purpose | URL |
|---|------|---------|-----|
| 18 | What are Mutual Funds | MF basics | https://www.amfiindia.com/investor-corner/knowledge-center/what-are-mutual-funds.html |
| 19 | Types of MF Schemes | Scheme types explained | https://www.amfiindia.com/investor-corner/knowledge-center/types-of-mutual-fund-schemes.html |
| 20 | Investor FAQ | General investor FAQs | https://www.amfiindia.com/investor-corner/investor-center/investor-faq.html |

### Source Diversity (Brief requires 15–25; corpus = 20 ✅)
AMC scheme pages, factsheets, KIM, SID, scheme FAQs, fee/charges (embedded in Groww pages), riskometer/benchmark notes, statement/tax-doc guides, SEBI pages (3), AMFI pages (3) — all covered.

### Data Available Per Groww Scheme Page
Expense ratio (direct), exit load, min SIP, min lumpsum, riskometer category, benchmark index, fund manager name(s)/tenure/education/experience, fund size (AUM), NAV, fund age/launch date, tax implications (STCG/LTCG), lock-in (ELSS), stamp duty (0.005%), scheme category.

---

## 6. Functional Requirements

### 6.1 Facts-Only Q&A — 17 Query Types
| # | Query Type | Expected Behavior |
|---|-----------|-------------------|
| 1 | Expense Ratio | Exact %, cite Groww page |
| 2 | Exit Load | Load structure + conditions, cite Groww page |
| 3 | Minimum SIP | ₹ amount, cite Groww page |
| 4 | Minimum Lumpsum | ₹ amount, cite Groww page |
| 5 | Risk Classification | Risk category, cite Groww/SEBI riskometer |
| 6 | Benchmark | Index name, cite Groww page |
| 7 | Fund Manager | Manager name(s), cite Groww page |
| 8 | Fund Manager Details | Tenure/education/experience, cite Groww page |
| 9 | Tax Implications | STCG/LTCG details, cite Groww page |
| 10 | Lock-in Period | "3 years mandatory" (ELSS), cite ELSS page |
| 11 | ELSS Tax Benefit | "Up to ₹1.5 lakh under Section 80C", cite HDFC ELSS page |
| 12 | Statement Download | Process, cite HDFC MF guide |
| 13 | CAS Download | Steps, cite HDFC MF CAS page |
| 14 | AUM / Fund Size | AUM in ₹ Cr, cite Groww page |
| 15 | SEBI Category | Category name, cite SEBI/Groww page |
| 16 | What is a Mutual Fund? | AMFI definition, cite AMFI page |
| 17 | Riskometer Explanation | SEBI explanation, cite SEBI riskometer |

### 6.2 Response Format (STRICT — every response)
- **Answer:** Maximum **3 sentences**, factual, plain language
- **Citation:** Exactly **one** source link from the 20-URL corpus
- **Freshness footer:** `"Last updated from sources: <date>"`

**Example:**
```
The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.74% (Direct Plan). This includes
the investment management and advisory fee, and other expenses as per SEBI regulations.

Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth

Last updated from sources: June 2026
```

### 6.3 Refusal Handling (6 advisory types)
Refuse: buy/sell recommendations, opinion-based comparisons, performance predictions, return calculations, portfolio advice, personal finance advice.

Every refusal MUST: be polite, reinforce facts-only limitation, provide a relevant educational link (AMFI/SEBI from corpus).

**Example:**
```
I'm a facts-only assistant and cannot provide investment recommendations or opinions.
For guidance on mutual fund investing, please refer to AMFI's investor education resources.

Source: https://www.amfiindia.com/investor-corner/knowledge-center/what-are-mutual-funds.html

Last updated from sources: June 2026
```

### 6.4 PII Detection & Rejection
| PII Type | Pattern | Action |
|----------|---------|--------|
| PAN | `[A-Z]{5}[0-9]{4}[A-Z]` | Reject immediately |
| Aadhaar | `\d{4}[\s-]?\d{4}[\s-]?\d{4}` | Reject immediately |
| Phone | `[6-9]\d{9}` (Indian mobile) | Reject immediately |
| Email | Standard email regex | Reject immediately |
| Account Number | 8–18 digit sequences | Reject immediately |
| OTP | 4–6 digit codes in context | Reject immediately |

PII rejection: refuse to process, explain why, never echo back the PII. Tagline: "Facts-only. No investment advice."

### 6.5 UI Requirements (Minimal)
1. Welcome message (scope: 6 HDFC MF schemes, facts-only)
2. 3 example questions pre-loaded
3. Visible disclaimer: `"Facts-only. No investment advice."`
4. Input field
5. Response area (answer + citation + last-updated footer)

Example questions: expense ratio of HDFC Mid Cap; lock-in for HDFC ELSS Tax Saver; how to download capital gains statement.

---

## 7. Hard Constraints (Violation = Fail)

### Data & Sources
- Public sources only (the 20 official URLs)
- Citations must come from the corpus
- No third-party blogs (Moneycontrol, ET Money, ValueResearch, etc.)
- No app back-end / internal screenshots
- Official sources only: AMC, Groww, SEBI, AMFI

### Privacy & Security
- No PII collection, storage, solicitation, or echo

### Content Restrictions
- No investment advice, performance comparisons, return calculations, predictions, or speculation
- Returns asked → link to official factsheet only

### Transparency & Format
- ≤3 sentences; exactly one citation link; last-updated footer always; verifiable facts; plain language

---

## 8. Technical Architecture (RAG Pipeline)

### Request Flow (4 Layers)
1. **Layer 1 — PII Guard:** Regex scan (PAN, Aadhaar, phone, email, OTP, acct#). If detected → reject; else pass on.
2. **Layer 2 — Query Classification:** Route to `FACTUAL`, `ADVISORY`, or `OUT_OF_SCOPE` (LLM-based or hybrid rules+LLM).
   - FACTUAL → Layer 3 RAG retrieval
   - ADVISORY → Safe refusal generator (educational link)
   - OUT_OF_SCOPE → Scope boundary response ("I only cover these 6 schemes")
3. **Layer 3 — RAG Retrieval:** Embed query → vector search → retrieve top-k chunks with metadata.
4. **Layer 4 — Answer Generation (LLM):** System prompt enforces ≤3 sentences, grounding only in retrieved context (no hallucination), include source_url, append last-updated date, no opinions/advice/performance claims.

Output: formatted response (answer + source + last-updated footer).

### Components
| # | Component | Implementation Options |
|---|-----------|------------------------|
| 1 | Web Scraper / Loader | BeautifulSoup, Playwright, LangChain WebLoader |
| 2 | Text Preprocessor | Custom Python |
| 3 | Text Splitter / Chunker | LangChain RecursiveCharacterTextSplitter |
| 4 | Metadata Tagger | Custom during ingestion |
| 5 | Embedding Model | OpenAI ada-002, HuggingFace sentence-transformers |
| 6 | Vector Store | ChromaDB / FAISS (local), Pinecone (cloud) |
| 7 | Retriever | Similarity search with score threshold |
| 8 | Query Classifier | LLM-based or hybrid |
| 9 | PII Detector | Regex (Indian PII formats) |
| 10 | LLM Generator | Groq (Llama 3.x) |
| 11 | Prompt Template | System prompt + few-shot |
| 12 | Citation Mapper | Metadata passthrough |

### Chunk Metadata Schema (every chunk)
```json
{
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "source_type": "groww_scheme_page | amc_official | sebi | amfi",
  "scheme_name": "HDFC Mid Cap Fund Direct Growth",
  "scheme_category": "Equity — Mid Cap",
  "data_type": "expense_ratio | exit_load | sip_details | risk | benchmark | fund_manager | tax | statement_guide | investor_education",
  "scrape_date": "2026-06-23",
  "chunk_index": 1
}
```
Enables accurate citation, freshness reporting, source filtering, and query routing.

---

## 9. Skills Evaluated (Rubric)

- **W1 — Thinking Like a Model:** Identify exact fact asked; decide answer vs refuse; handle ambiguity; distinguish scheme-specific vs general. Success = correct data type, no advisory leakage, no hallucination.
- **W2 — LLMs & Prompting:** Instruction-style prompting; concise phrasing; safe refusals; natural citation wording. Success = ≤3 sentences + citation + date every time.
- **W3 — RAGs (Primary Skill):** Small-corpus retrieval; accurate citations; grounding; chunk quality; multi-source retrieval. Success = right scheme + right data type, zero hallucination, verifiable links.

---

## 10. Edge Cases & Failure Modes

| # | Edge Case | Expected Behavior |
|---|-----------|-------------------|
| 1 | Scheme not in corpus | List the 6 covered schemes; suggest hdfcfund.com |
| 2 | User provides PII | Reject, explain, do not process or echo |
| 3 | Returns/performance asked | Refuse, link to factsheet portal |
| 4 | Ambiguous query | Default to factual if possible; else clarify |
| 5 | Source updated since scrape | Show "Last updated from sources: <date>" |
| 6 | Two schemes in one query | Answer both if clear; else clarify |
| 7 | Hindi/regional query | Answer in English or state language limit |
| 8 | Answer not in corpus | Admit "I don't have this information" — never hallucinate |
| 9 | General MF concept | Answer from AMFI/SEBI corpus pages |
| 10 | Manager of multiple schemes | Return all relevant corpus associations |
| 11 | Regular plan query (corpus = Direct only) | State Direct-only; link AMC |
| 12 | Lock-in for non-ELSS fund | "This fund has no lock-in period"; cite scheme page |
| 13 | ELSS tax benefit amount | "Up to ₹1.5 lakh under Section 80C"; cite ELSS page |

---

## 11. Deliverables

### Submission Checklist
1. Working prototype (live link OR ≤3-min demo video) — linked in README
2. Source list (20 URLs, markdown table) — in README
3. README.md (all required sections) — repo root
4. Sample Q&A (5–10 queries with answers + links) — in README
5. Disclaimer snippet — in README + UI: `"Facts-only. No investment advice."`
6. GitHub link — single submission point

### README.md Structure
Overview · Product Context · Schemes Covered (6) · Setup Instructions · Architecture (RAG diagram) · Source List (20 URLs) · Sample Q&A (5–10) · Disclaimer · Known Limitations.

---

## 12. Success Criteria (Definition of Done)

1. Accurately retrieves all 17 factual query types
2. Strict facts-only (zero opinion/advice leakage)
3. Valid corpus citation in every answer (100%)
4. Proper refusal of all 6 advisory types
5. PII detection & rejection (PAN, Aadhaar, phone, email, OTP)
6. Answers ≤3 sentences (never exceeds)
7. "Last updated from sources: <date>" always present
8. UI has welcome + 3 examples + disclaimer
9. 20 source URLs documented in README
10. All sources official/public (domain verified)
11. ELSS lock-in queries → "3 years"
12. Statement download queries → process + link
13. SEBI/AMFI educational queries answered from corpus
14. No hallucination (admits when unknown)
15. README complete per structure

---

## 13. Known Limitations (Document in README)

| # | Limitation | Mitigation |
|---|-----------|------------|
| 1 | 20-URL corpus (not exhaustive) | State scope in UI; suggest hdfcfund.com |
| 2 | Data freshness depends on scrape date | Show "Last updated"; support re-scraping |
| 3 | Direct Growth plans only | State in welcome; link AMC for other plans |
| 4 | English only | State language limitation |
| 5 | Single-turn (initially) | Each query independent |
| 6 | Groww data may lag AMC updates | Cite source; show scrape date |
| 7 | PDF factsheets need periodic refresh | Document refresh recommendation |

---

## 14. Glossary

| Abbr. | Full Form | Description |
|-------|-----------|-------------|
| AMC | Asset Management Company | Manages MF schemes (HDFC MF) |
| MF | Mutual Fund | Pool invested in securities |
| ELSS | Equity Linked Savings Scheme | Tax-saving MF, 3-yr lock-in (80C) |
| SIP | Systematic Investment Plan | Periodic fixed investment |
| SEBI | Securities and Exchange Board of India | Market regulator |
| AMFI | Association of Mutual Funds in India | Industry body; investor education |
| KIM | Key Information Memorandum | Summary scheme document |
| SID | Scheme Information Document | Detailed scheme document |
| SAI | Statement of Additional Information | Supplementary legal document |
| CAS | Consolidated Account Statement | Combined MF/demat holdings statement |
| RAG | Retrieval-Augmented Generation | Retrieval + generative AI |
| PII | Personally Identifiable Information | PAN, Aadhaar, phone, email, acct#, OTP |
| PAN | Permanent Account Number | 10-char tax identifier |
| OTP | One-Time Password | Short-lived auth code |
| LLM | Large Language Model | Language understanding/generation model |
| NAV | Net Asset Value | Per-unit price of a scheme |
| AUM | Assets Under Management | Total value managed |
| STCG | Short Term Capital Gains | Tax on gains < 1 yr (equity) |
| LTCG | Long Term Capital Gains | Tax on gains > 1 yr (equity) |
| FoF | Fund of Funds | MF investing in other MFs/ETFs |
| ETF | Exchange Traded Fund | Exchange-traded fund |
| KYC | Know Your Customer | Identity verification |
| W1/W2/W3 | Week 1/2/3 | Skills: Thinking Like a Model, Prompting, RAGs |

---

*Source: `Problem Statement — MF FAQ Chatbot.md` (Version 4.0, Final). This context.md is a condensed working reference; the original problem statement remains authoritative.*
