# Problem Statement: RAG-Based Mutual Fund FAQ Chatbot

> **Deadline:** June 26, 2026 — 11:59 PM IST  
> **Product Context:** Groww  
> **Selected AMC:** HDFC Mutual Fund ([hdfcfund.com](http://www.hdfcfund.com))  
> **Corpus:** 20 official public URLs (Groww scheme pages + AMC + SEBI + AMFI)  
> **Submission:** Have to data architecture, build Fronend, Backend, full working product, GitHub Link (README must include source list, sample Q&A, disclaimer)  and more
> **Carry-Forward Rule:** Groww is locked in for ALL subsequent milestones.

---

## 1. Overview

The objective of this project is to build a **facts-only FAQ assistant** for mutual fund schemes, using **Groww** as the reference product context. The assistant will answer objective, verifiable queries related to mutual funds by retrieving information exclusively from **official public sources** — Groww scheme pages, HDFC Mutual Fund's official website, SEBI, and AMFI.

The system must **strictly avoid** providing investment advice, opinions, or recommendations. Every response must include a **single, clear source link** and adhere to defined constraints around clarity, accuracy, and compliance.

### Core Principle
> Build a trustworthy, transparent, and compliant mutual fund FAQ assistant that prioritizes **accuracy over intelligence**. The system ensures users receive only verified, source-backed financial information, without any advisory bias or speculative content.

---

## 2. Problem Context & Rationale

### 2.1 The User Pain Point

Retail mutual fund investors in India face a recurring friction: **finding accurate, factual answers** about specific scheme details — expense ratios, exit loads, minimum SIP amounts, lock-in periods, riskometer categories, benchmarks, fund manager details, and how to download statements or tax documents.

These are **not opinion questions** — they have definitive, source-verifiable answers scattered across AMC websites, factsheets, KIMs, SIDs, SEBI circulars, AMFI portals, and platform pages like Groww.

Currently, users either:
- Dig through multiple pages and PDFs manually
- Call AMC helplines and wait
- Ask on forums and get unreliable/outdated answers
- Rely on fintech app FAQs that may be incomplete or generic

### 2.2 Target Users

| Audience | Use Case |
|----------|----------|
| **Retail investors** | Comparing mutual fund schemes before investing — need quick, sourced facts |
| **Customer support teams** | Handling repetitive MF factual queries without manual lookup |
| **Content teams** | Validating scheme details for articles/comparisons |

### 2.3 What This Is NOT

- ❌ An investment advisor ("Should I buy X?")
- ❌ A returns calculator or performance comparator
- ❌ A portfolio manager or rebalancer
- ❌ A KYC/account management tool
- ❌ A general financial chatbot

---

## 3. Objective

Design and implement a lightweight **Retrieval-Augmented Generation (RAG)-based** assistant that:

1. **Answers factual queries** about 6 HDFC Mutual Fund schemes (across 5 equity categories + 1 commodity)
2. **Uses a curated corpus** of 20 official public URLs (Groww + AMC + SEBI + AMFI)
3. **Provides concise, source-backed responses** (≤3 sentences + one citation link + last-updated date)
4. **Refuses advisory/opinion queries** politely with an educational link
5. **Guards against PII** — never accepts or stores personal data
6. **Handles fund management queries** — fund manager names, tenure, education, professional experience
7. **Handles document access queries** — how to download statements, CAS, capital gains reports

---

## 4. Scope of Work

### 4.1 Selected AMC

**HDFC Mutual Fund** — [www.hdfcfund.com](http://www.hdfcfund.com)

### 4.2 Corpus Definition (20 Official Public URLs)

#### A. Groww Scheme Pages (6 URLs) — Primary scheme fact source

| # | Scheme Name | Category | URL |
|---|-------------|----------|-----|
| 1 | HDFC Mid Cap Fund Direct Growth | Equity — Mid Cap | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| 2 | HDFC Large Cap Fund Direct Growth | Equity — Large Cap | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 3 | HDFC Small Cap Fund Direct Growth | Equity — Small Cap | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 4 | HDFC Flexi Cap Fund Direct Growth | Equity — Flexi Cap | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 5 | HDFC ELSS Tax Saver Fund Direct Plan Growth | Equity — ELSS (Tax Saver) | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| 6 | HDFC Gold ETF Fund of Fund Direct Plan Growth | Commodities — Gold | https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth |

#### B. HDFC Mutual Fund Official (AMC) Pages (8 URLs) — Factsheets, KIM, SID, FAQs, statement guides

| # | Page | Purpose | URL |
|---|------|---------|-----|
| 7 | HDFC MF Factsheets Portal | Monthly factsheets (all schemes) | https://www.hdfcfund.com/mutual-funds/factsheets |
| 8 | HDFC MF KIM Documents | Key Information Memorandum (all schemes) | https://www.hdfcfund.com/mutual-funds/fund-documents/kim |
| 9 | HDFC MF Offer Documents (SID/SAI) | Scheme Information Documents | https://www.hdfcfund.com/statutory-disclosure/offer-document-disclosures |
| 10 | HDFC ELSS Tax Saver — Official Page | AMC scheme page (lock-in, tax benefits) | https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver/direct |
| 11 | How to Get Capital Gains Statement | Guide for downloading capital gains report | https://www.hdfcfund.com/learn/blog/how-get-capital-gain-statement-mutual-fund-schemes-india |
| 12 | Download Consolidated Account Statement | CAS download process | https://www.hdfcfund.com/services/consolidated-account-statement |
| 13 | CAS FAQ (HDFC MF) | Frequently asked questions about CAS | https://www.hdfcfund.com/services/faqs/consolidated-account-statement |
| 14 | Subscription-Related FAQs | KYC, SID, KIM references, investment process | https://www.hdfcfund.com/services/faqs/subscription-related-faqs |

#### C. SEBI Official Pages (3 URLs) — Regulatory, riskometer, categorization

| # | Page | Purpose | URL |
|---|------|---------|-----|
| 15 | SEBI Riskometer Guide | Understanding risk levels in mutual funds | https://investor.sebi.gov.in/riskometer.html |
| 16 | SEBI MF Categorization Circular | Scheme categorization rules (Large/Mid/Small/Flexi/ELSS) | https://www.sebi.gov.in/legal/circulars/oct-2017/categorization-and-rationalization-of-the-schemes-offered-by-mutual-funds_36199.html |
| 17 | Groww Blog: Guide to SEBI Categories | SEBI categorization explained (official Groww content) | https://groww.in/blog/guide-to-sebi-new-categories-of-mutual-fund |

#### D. AMFI Official Pages (3 URLs) — Investor education, mutual fund basics

| # | Page | Purpose | URL |
|---|------|---------|-----|
| 18 | AMFI: What are Mutual Funds | Investor education — MF basics | https://www.amfiindia.com/investor-corner/knowledge-center/what-are-mutual-funds.html |
| 19 | AMFI: Types of Mutual Fund Schemes | Scheme types explained | https://www.amfiindia.com/investor-corner/knowledge-center/types-of-mutual-fund-schemes.html |
| 20 | AMFI: Investor FAQ | General investor FAQs | https://www.amfiindia.com/investor-corner/investor-center/investor-faq.html |

### 4.3 Scheme Coverage & Diversity

| Category | Scheme | Why Included |
|----------|--------|-------------|
| **Equity — Large Cap** | HDFC Large Cap Fund | Low-to-moderate risk; large-cap queries |
| **Equity — Mid Cap** | HDFC Mid Cap Fund | Moderate risk; mid-cap queries |
| **Equity — Small Cap** | HDFC Small Cap Fund | High risk; small-cap queries |
| **Equity — Flexi Cap** | HDFC Flexi Cap Fund | Multi-cap flexibility; originally suggested in brief |
| **Equity — ELSS (Tax Saver)** | HDFC ELSS Tax Saver | 3-year lock-in; tax benefit queries (Section 80C) |
| **Commodities — Gold** | HDFC Gold ETF FoF | Non-equity; gold/commodity queries; Fund-of-Funds structure |

This coverage ensures:
- ✅ Large-cap, Mid-cap, Small-cap, Flexi-cap, ELSS — all suggested categories covered
- ✅ One non-equity (Gold) for diversity
- ✅ Lock-in period testable (ELSS = 3 years mandatory)
- ✅ Different risk levels (Moderate to Very High)
- ✅ Different structures (direct equity, FoF, tax-saver)

### 4.4 Source Diversity Validation

| Source Type | Required by Brief | Count in Corpus | Status |
|-------------|------------------|-----------------|--------|
| AMC scheme pages | ✅ | 6 (Groww) + 1 (HDFC MF ELSS) | ✅ Covered |
| Factsheets | ✅ | 1 (factsheet portal) | ✅ Covered |
| KIM | ✅ | 1 (KIM portal) | ✅ Covered |
| SID | ✅ | 1 (offer documents) | ✅ Covered |
| Scheme FAQs | ✅ | 2 (CAS FAQ + subscription FAQ) | ✅ Covered |
| Fee/charges pages | ✅ | Embedded in Groww scheme pages | ✅ Covered |
| Riskometer/benchmark notes | ✅ | 1 (SEBI riskometer) + 1 (SEBI categorization) | ✅ Covered |
| Statement/tax-doc guides | ✅ | 2 (capital gains + CAS download) | ✅ Covered |
| SEBI pages | ✅ | 3 | ✅ Covered |
| AMFI pages | ✅ | 3 | ✅ Covered |
| **Total** | **15–25** | **20** | ✅ **Within range** |

### 4.5 Data Available Per Groww Scheme Page

Each Groww scheme page contains:

| Data Point | Available? | Notes |
|------------|-----------|-------|
| Expense Ratio (Direct) | ✅ | Clearly listed as percentage |
| Exit Load | ✅ | Structure with time-based conditions |
| Minimum SIP Amount | ✅ | ₹ value |
| Minimum Lumpsum Amount | ✅ | ₹ value |
| Riskometer Category | ✅ | Risk level (Low/Moderate/High/Very High) |
| Benchmark Index | ✅ | Index name |
| Fund Manager Name(s) | ✅ | Current manager(s) |
| Fund Manager Tenure | ✅ | Duration managing this scheme |
| Fund Manager Education | ✅ | Degrees/qualifications |
| Fund Manager Experience | ✅ | Professional background |
| Fund Size (AUM) | ✅ | Assets Under Management in ₹ Cr |
| NAV | ✅ | Current Net Asset Value |
| Fund Age / Launch Date | ✅ | Scheme inception date |
| Tax Implications (STCG/LTCG) | ✅ | Capital gains tax rules |
| Lock-in Period | ✅ | Shown for ELSS ("3Y Lock-in") |
| Stamp Duty | ✅ | 0.005% on investments |
| Scheme Category | ✅ | SEBI category classification |

---

## 5. Functional Requirements

### 5.1 Core Capability: Facts-Only Q&A

The assistant MUST answer the following **fact categories** accurately with citations:

| # | Query Type | Example Query | Expected Behavior |
|---|-----------|---------------|-------------------|
| 1 | **Expense Ratio** | "What is the expense ratio of HDFC Mid Cap Fund?" | Return exact %, cite Groww page |
| 2 | **Exit Load** | "Exit load for HDFC Small Cap Fund?" | Return load structure with conditions, cite Groww page |
| 3 | **Minimum SIP** | "Minimum SIP amount for HDFC Large Cap Fund?" | Return ₹ amount, cite Groww page |
| 4 | **Minimum Lumpsum** | "Minimum investment in HDFC Flexi Cap Fund?" | Return ₹ amount, cite Groww page |
| 5 | **Risk Classification** | "Riskometer of HDFC Gold ETF FoF?" | Return risk category, cite Groww page or SEBI riskometer |
| 6 | **Benchmark** | "What's the benchmark for HDFC Mid Cap Fund?" | Return index name, cite Groww page |
| 7 | **Fund Manager** | "Who manages HDFC ELSS Tax Saver?" | Return manager name(s), cite Groww page |
| 8 | **Fund Manager Details** | "What is the experience of the fund manager of HDFC Mid Cap Fund?" | Return tenure/education/experience, cite Groww page |
| 9 | **Tax Implications** | "What are the tax rules for HDFC Small Cap Fund?" | Return STCG/LTCG details, cite Groww page |
| 10 | **Lock-in Period** | "What's the lock-in period for HDFC ELSS Tax Saver?" | Return "3 years mandatory", cite ELSS page |
| 11 | **ELSS Tax Benefit** | "How much tax deduction can I claim with ELSS?" | Return "up to ₹1.5 lakh under Section 80C", cite HDFC MF ELSS page |
| 12 | **Statement Download** | "How to download capital-gains statement?" | Return process, cite HDFC MF guide |
| 13 | **CAS Download** | "How to get consolidated account statement?" | Return steps, cite HDFC MF CAS page |
| 14 | **AUM / Fund Size** | "What is the fund size of HDFC Large Cap Fund?" | Return AUM in ₹ Cr, cite Groww page |
| 15 | **SEBI Category** | "What SEBI category is HDFC Flexi Cap Fund?" | Return "Flexi Cap", cite SEBI categorization or Groww page |
| 16 | **What is a Mutual Fund?** | "What is a mutual fund?" | Return AMFI definition, cite AMFI page |
| 17 | **Riskometer Explanation** | "What does the riskometer mean?" | Return SEBI explanation, cite SEBI riskometer page |

### 5.2 Response Format Requirements (STRICT)

Every response from the assistant MUST follow this exact format:

| Element | Specification | Mandatory? |
|---------|---------------|-----------|
| **Answer** | Maximum **3 sentences** — factual, clear, plain language | ✅ Yes |
| **Citation** | Exactly **one** source link (must be from the 20-URL corpus) | ✅ Yes |
| **Freshness footer** | `"Last updated from sources: <date>"` | ✅ Yes |

**Example response format:**
```
The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.74% (Direct Plan). This includes 
the investment management and advisory fee, and other expenses as per SEBI regulations.

Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth

Last updated from sources: June 2026
```

### 5.3 Refusal Handling (Safe Refusals)

The assistant MUST refuse **non-factual or advisory queries**:

| # | Refused Query Type | Example | Required Response Pattern |
|---|-------------------|---------|--------------------------|
| 1 | Buy/Sell recommendation | "Should I invest in HDFC Mid Cap Fund?" | Polite refusal + educational link |
| 2 | Fund comparison (opinion) | "Which is better — Mid Cap or Flexi Cap?" | Polite refusal + educational link |
| 3 | Performance prediction | "Will HDFC ELSS NAV go up?" | Polite refusal + factsheet link |
| 4 | Return calculations | "What returns will I get from HDFC Small Cap?" | Polite refusal + factsheet link |
| 5 | Portfolio advice | "Should I add Gold ETF to my portfolio?" | Polite refusal + educational link |
| 6 | Personal finance advice | "How much SIP should I do monthly?" | Polite refusal + educational link |

**Every refusal MUST:**
1. Be polite and clearly worded
2. Reinforce the facts-only limitation explicitly
3. Provide a relevant educational link (AMFI investor education or SEBI resource from corpus)

**Example refusal:**
```
I'm a facts-only assistant and cannot provide investment recommendations or opinions. 
For guidance on mutual fund investing, please refer to AMFI's investor education resources.

Source: https://www.amfiindia.com/investor-corner/knowledge-center/what-are-mutual-funds.html

Last updated from sources: June 2026
```

### 5.4 PII Detection & Rejection

The assistant MUST detect and reject any input containing personally identifiable information:

| PII Type | Pattern | Action |
|----------|---------|--------|
| **PAN** | `[A-Z]{5}[0-9]{4}[A-Z]` | Reject immediately |
| **Aadhaar** | `\d{4}[\s-]?\d{4}[\s-]?\d{4}` | Reject immediately |
| **Phone** | `[6-9]\d{9}` (Indian mobile) | Reject immediately |
| **Email** | Standard email regex | Reject immediately |
| **Account Number** | Long digit sequences (8-18 digits) | Reject immediately |
| **OTP** | 4-6 digit codes in context | Reject immediately |

**PII rejection response:**
```
I cannot process requests containing personal information (PAN, Aadhaar, phone numbers, 
email addresses, or account numbers). Please rephrase your question without personal details.

Facts-only. No investment advice.
```

### 5.5 User Interface Requirements (Minimal)

The solution MUST include a simple interface with:

| # | Element | Specification |
|---|---------|---------------|
| 1 | **Welcome message** | Brief greeting explaining scope (6 HDFC MF schemes, facts-only) |
| 2 | **3 example questions** | Pre-loaded visible examples |
| 3 | **Disclaimer** | Visible text: `"Facts-only. No investment advice."` |
| 4 | **Input field** | Text input for user queries |
| 5 | **Response area** | Formatted answer with citation + last-updated footer |

**Example questions to display:**
1. "What is the expense ratio of HDFC Mid Cap Fund?"
2. "What's the lock-in period for HDFC ELSS Tax Saver?"
3. "How to download my capital gains statement?"

---

## 6. Constraints (HARD — Violation = Fail)

### 6.1 Data & Sources

| # | Constraint | Detail |
|---|-----------|--------|
| 1 | **Public sources only** | Corpus limited to the 20 official URLs in Section 4.2 |
| 2 | **Citations from corpus** | Responses MUST cite one of the 20 corpus URLs |
| 3 | **No third-party blogs** | No Moneycontrol, ET Money, ValueResearch, or any non-official source |
| 4 | **No app back-end** | Cannot use screenshots of internal app pages |
| 5 | **Official sources only** | AMC (hdfcfund.com), Platform (groww.in), Regulator (sebi.gov.in), Industry body (amfiindia.com) |

### 6.2 Privacy & Security

| # | Constraint | Detail |
|---|-----------|--------|
| 1 | **No PII collection** | Must NOT collect PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers |
| 2 | **No PII storage** | Even if accidentally provided, must not store or process |
| 3 | **No PII solicitation** | Must never ask users for personal identifying information |
| 4 | **No PII echo** | If PII detected in input, do NOT repeat it back |

### 6.3 Content Restrictions

| # | Constraint | Detail |
|---|-----------|--------|
| 1 | **No investment advice** | No recommendations, opinions, or suggestions |
| 2 | **No performance comparisons** | Must not compute, compare, or state returns across schemes |
| 3 | **No return calculations** | If returns asked → link to official factsheet only |
| 4 | **No predictions** | No future NAV predictions, no "better/worse" judgments |
| 5 | **No speculative content** | Only verifiable facts from the corpus |

### 6.4 Transparency & Format

| # | Constraint | Detail |
|---|-----------|--------|
| 1 | **≤ 3 sentences** | Every answer must be 3 sentences or fewer |
| 2 | **One citation link** | Exactly one source URL per response — always |
| 3 | **Last-updated footer** | `"Last updated from sources: <date>"` — always |
| 4 | **Verifiable** | User can click the source link and find the stated fact |
| 5 | **Plain language** | No unexplained jargon |

---

## 7. Technical Architecture (RAG Pipeline)

### 7.1 High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                               │
│         (e.g., "What is the lock-in for HDFC ELSS?")            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 1: PII GUARD                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Regex scan for: PAN, Aadhaar, phone, email, OTP, acct#  │  │
│  │  If detected → REJECT immediately, return PII message     │  │
│  │  If clean → pass to next layer                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ [Clean input]
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LAYER 2: QUERY CLASSIFICATION                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Classify intent:                                          │  │
│  │    → FACTUAL (expense ratio, exit load, SIP, manager...)  │  │
│  │    → ADVISORY (should I buy, which is better, predict...) │  │
│  │    → OUT_OF_SCOPE (scheme not in corpus, unrelated...)    │  │
│  │                                                            │  │
│  │  Method: LLM-based or hybrid (rules + LLM)                │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────┬────────────────────┬────────────────┬──────────────┘
             │                    │                │
      [FACTUAL]            [ADVISORY]       [OUT_OF_SCOPE]
             │                    │                │
             ▼                    ▼                ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
│  LAYER 3: RAG   │  │  SAFE REFUSAL    │  │  SCOPE BOUNDARY     │
│  RETRIEVAL      │  │  GENERATOR       │  │  RESPONSE           │
│                 │  │                  │  │                     │
│  • Embed query  │  │  • Polite msg    │  │  • "I only cover    │
│  • Search vector│  │  • Facts-only    │  │    these 6 schemes" │
│    store        │  │    reinforcement │  │  • Link to AMC site │
│  • Retrieve     │  │  • Educational   │  │    for other queries │
│    top-k chunks │  │    link (AMFI/   │  │                     │
│  • Return with  │  │    SEBI from     │  │                     │
│    metadata     │  │    corpus)       │  │                     │
└────────┬────────┘  └──────────────────┘  └─────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LAYER 4: ANSWER GENERATION (LLM)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  System Prompt enforces:                                   │  │
│  │    • ≤3 sentences only                                     │  │
│  │    • Ground ONLY in retrieved context (no hallucination)   │  │
│  │    • Include source_url from chunk metadata                │  │
│  │    • Append "Last updated from sources: <date>"            │  │
│  │    • No opinions, no advice, no performance claims         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FORMATTED RESPONSE                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  [Answer: ≤3 sentences, factual, grounded]                │  │
│  │  [Source: <one URL from corpus>]                          │  │
│  │  [Last updated from sources: <date>]                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 RAG Pipeline Components

| # | Component | Purpose | Implementation Options |
|---|-----------|---------|----------------------|
| 1 | **Web Scraper / Document Loader** | Extract text from 20 URLs (HTML pages + PDFs) | BeautifulSoup, Playwright, LangChain WebLoader |
| 2 | **Text Preprocessor** | Clean HTML, normalize text, extract structured fields | Custom Python scripts |
| 3 | **Text Splitter / Chunker** | Split content into retrievable chunks | LangChain RecursiveCharacterTextSplitter |
| 4 | **Metadata Tagger** | Attach `{source_url, source_type, scheme_name, data_type, scrape_date}` | Custom during ingestion |
| 5 | **Embedding Model** | Convert chunks to vector representations | OpenAI ada-002, HuggingFace sentence-transformers |
| 6 | **Vector Store** | Store embeddings for similarity search | ChromaDB (local), FAISS (local), Pinecone (cloud) |
| 7 | **Retriever** | Find top-k relevant chunks for a query | Similarity search with score threshold |
| 8 | **Query Classifier** | Route: factual / advisory / out-of-scope | LLM-based or hybrid (rules + LLM) |
| 9 | **PII Detector** | Block personal data before any processing | Regex patterns for Indian PII formats |
| 10 | **LLM (Generator)** | Generate grounded answer from retrieved context | GPT-4o-mini, Grok, Gemini, or open-source |
| 11 | **Prompt Template** | Enforce all format constraints | System prompt + few-shot examples |
| 12 | **Citation Mapper** | Extract source_url from chunk metadata → insert in response | Metadata passthrough |

### 7.3 Chunk Metadata Schema

Every chunk stored in the vector store MUST carry:

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

This metadata enables:
- **Accurate citation** — source_url flows directly into the response
- **Freshness reporting** — scrape_date → "Last updated from sources"
- **Source filtering** — source_type helps prioritize retrieval
- **Query routing** — data_type helps match queries to relevant chunks

---

## 8. Skills Being Evaluated (Rubric Mapping)

### 8.1 W1 — Thinking Like a Model

| What's Tested | How It's Evaluated | Success Indicator |
|---------------|-------------------|-------------------|
| Identify the exact fact being asked | System correctly parses "expense ratio of X" vs. "is X good?" | Returns correct data type |
| Decide: answer vs. refuse | Binary classification accuracy on edge cases | No advisory leakage |
| Handle ambiguous queries | Graceful clarification or best-match retrieval | Doesn't hallucinate |
| Distinguish scheme-specific vs. general queries | Routes correctly | Answers facts, refuses opinions |

### 8.2 W2 — LLMs & Prompting

| What's Tested | How It's Evaluated | Success Indicator |
|---------------|-------------------|-------------------|
| Instruction-style prompting | System prompt enforces all constraints | ≤3 sentences, citation, date — every time |
| Concise phrasing | Answer length check | Never exceeds 3 sentences |
| Safe refusals | Polite, non-judgmental tone | Includes educational link, reinforces facts-only |
| Citation wording | Natural source integration | Link is relevant and clickable |

### 8.3 W3 — RAGs (Primary Skill)

| What's Tested | How It's Evaluated | Success Indicator |
|---------------|-------------------|-------------------|
| Small-corpus retrieval | Correct chunk from 20 pages | Right scheme + right data type |
| Accurate citations | Source link contains the stated fact | User can verify by clicking |
| Grounding | Answer faithful to retrieved content | Zero hallucination |
| Chunk quality | Appropriate granularity | No truncated or irrelevant chunks |
| Multi-source retrieval | Can pull from Groww + AMC + SEBI + AMFI | Different source types used correctly |

---

## 9. Edge Cases & Failure Modes

| # | Edge Case | Expected Behavior |
|---|-----------|-------------------|
| 1 | Scheme NOT in corpus (e.g., HDFC Balanced Advantage) | "I cover HDFC Mid Cap, Large Cap, Small Cap, Flexi Cap, ELSS Tax Saver, and Gold ETF FoF. For other schemes, visit https://www.hdfcfund.com" |
| 2 | User provides PII | Immediately reject, explain why, do NOT process or echo back |
| 3 | User asks for returns/performance | Refuse politely, link to factsheet portal |
| 4 | Ambiguous query (factual or opinion) | Default to factual interpretation if possible; clarify otherwise |
| 5 | Source updated since scraping | "Last updated from sources: \<date\>" shows freshness |
| 6 | Two schemes in one query | Answer both if chunks are clear; clarify if ambiguous |
| 7 | Hindi/regional language query | Answer in English or state language limitation |
| 8 | Answer not in corpus | Admit "I don't have this information in my sources" — NEVER hallucinate |
| 9 | General MF concept question | Answer from AMFI/SEBI pages in corpus; cite educational link |
| 10 | Fund manager managing multiple listed schemes | Return all relevant associations from corpus |
| 11 | Regular plan query (corpus has Direct only) | "My information covers Direct plans. For Regular plan details, visit [AMC link]" |
| 12 | Query about lock-in for non-ELSS fund | "This fund has no lock-in period" — cite scheme page |
| 13 | Query about ELSS tax benefit amount | "Up to ₹1.5 lakh under Section 80C" — cite HDFC ELSS page |

---

## 10. Expected Deliverables

### 10.1 Submission Checklist

| # | Deliverable | Format | Where | Notes |
|---|-------------|--------|-------|-------|
| 1 | **Working Prototype** | Live link OR ≤3-min demo video | Linked in GitHub README | App/notebook |
| 2 | **Source List** | Markdown table | In README.md | 20 URLs with descriptions |
| 3 | **README.md** | Markdown | GitHub repo root | All required sections |
| 4 | **Sample Q&A** | Markdown | In README.md | 5–10 queries with answers + links |
| 5 | **Disclaimer Snippet** | Text | In README.md + in UI | `"Facts-only. No investment advice."` |
| 6 | **GitHub Link** | URL | Submission form | Single submission point |

### 10.2 README.md Structure

```markdown
# Mutual Fund FAQ Assistant — HDFC Mutual Fund (Groww)

## Overview
[Brief description of the project]

## Product Context
- Platform: Groww
- AMC: HDFC Mutual Fund (hdfcfund.com)

## Schemes Covered
| # | Scheme | Category |
[6 schemes table]

## Setup Instructions
[How to install and run locally]

## Architecture
[RAG pipeline overview with diagram]

## Source List (20 URLs)
[Full table from Section 4.2]

## Sample Q&A (5-10 Examples)
[Queries with full assistant responses including citations]

## Disclaimer
Facts-only. No investment advice.

## Known Limitations
[Corpus scope, freshness, language, Direct plans only, etc.]
```

---

## 11. Success Criteria (Definition of Done)

| # | Criterion | Test Method | Pass/Fail |
|---|-----------|-------------|-----------|
| 1 | Accurately retrieves factual MF information (all 17 query types) | Test each query type | All correct |
| 2 | Strict adherence to facts-only responses | No opinion/advice in any answer | Zero leakage |
| 3 | Consistent inclusion of valid source citations from corpus | Every answer has one working link | 100% rate |
| 4 | Proper refusal of advisory queries | Test all 6 refusal types | All refused properly |
| 5 | PII detection and rejection | Test with PAN, Aadhaar, phone, email, OTP | All detected |
| 6 | Answers ≤3 sentences | Sentence count check | Never exceeds |
| 7 | "Last updated from sources: \<date\>" present | Check every response | Always present |
| 8 | UI has welcome + 3 examples + disclaimer | Visual check | All visible |
| 9 | 20 source URLs documented in README | Count check | Complete |
| 10 | All sources are official/public | Domain verification | All verified |
| 11 | ELSS lock-in queries work | Test lock-in question | Correct "3 years" |
| 12 | Statement download queries work | Test CAS/capital gains question | Process explained with link |
| 13 | SEBI/AMFI educational queries work | Test "what is mutual fund?" | Answered from corpus |
| 14 | No hallucination | Ask about facts not in corpus | Admits "I don't know" |
| 15 | README complete per structure | Section check | All present |

---

## 12. Known Limitations (To Document in README)

| # | Limitation | Impact | Mitigation |
|---|-----------|--------|------------|
| 1 | 20-URL corpus (not exhaustive) | Cannot answer about non-HDFC schemes or all HDFC schemes | State scope in UI; suggest hdfcfund.com |
| 2 | Data freshness depends on scrape date | Expense ratios, AUM, NAV may change | Show "Last updated" date; architecture supports re-scraping |
| 3 | Direct Growth plans only | Cannot answer about Regular plans or IDCW options | State in welcome; link to AMC for other plans |
| 4 | English only | Cannot handle Hindi/regional queries | State language limitation |
| 5 | Single-turn (initially) | No conversation memory or follow-ups | Each query independent |
| 6 | Groww data may lag AMC updates | Minor discrepancies possible | Cite source; show scrape date |
| 7 | PDF factsheets may need periodic refresh | Data could become stale | Document refresh frequency recommendation |

---

## 13. Glossary

| Abbreviation | Full Form | Description |
|---|---|---|
| **AMC** | Asset Management Company | Manages mutual fund schemes (here: HDFC MF) |
| **MF** | Mutual Fund | Pool of money invested in securities |
| **ELSS** | Equity Linked Savings Scheme | Tax-saving MF with 3-year mandatory lock-in (Section 80C) |
| **SIP** | Systematic Investment Plan | Fixed-amount periodic investment method |
| **SEBI** | Securities and Exchange Board of India | Market regulator |
| **AMFI** | Association of Mutual Funds in India | Industry standards body; investor education |
| **KIM** | Key Information Memorandum | Summary document with essential scheme details |
| **SID** | Scheme Information Document | Comprehensive detailed scheme document |
| **SAI** | Statement of Additional Information | Supplementary legal document for MF schemes |
| **CAS** | Consolidated Account Statement | Combined statement of all MF/demat holdings |
| **RAG** | Retrieval-Augmented Generation | Retrieval + generative AI for grounded responses |
| **PII** | Personally Identifiable Information | PAN, Aadhaar, phone, email, account numbers, OTPs |
| **PAN** | Permanent Account Number | 10-character tax identifier |
| **OTP** | One-Time Password | Short-lived authentication code |
| **LLM** | Large Language Model | AI model for language understanding/generation |
| **NAV** | Net Asset Value | Per-unit price of a mutual fund scheme |
| **AUM** | Assets Under Management | Total value managed by a fund |
| **STCG** | Short Term Capital Gains | Tax on gains held < 1 year (equity) |
| **LTCG** | Long Term Capital Gains | Tax on gains held > 1 year (equity) |
| **FoF** | Fund of Funds | MF that invests in other MFs/ETFs |
| **ETF** | Exchange Traded Fund | Fund traded on stock exchange |
| **KYC** | Know Your Customer | Identity verification process |
| **W1 / W2 / W3** | Week 1 / Week 2 / Week 3 | Skills: Thinking Like a Model, Prompting, RAGs |

---

*Document Version: 4.0 (Final — 100% Assignment Coverage)*  
*Created: June 23, 2026*  
*Status: Ready for implementation*
