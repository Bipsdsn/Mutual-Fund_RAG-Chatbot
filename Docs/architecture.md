# Architecture: RAG-Based Mutual Fund FAQ Chatbot

> Detailed technical architecture derived from `Docs/context.md` and `Problem Statement — MF FAQ Chatbot.md`.
> This document defines the system design, components, data flow, technology choices, and operational concerns for the facts-only HDFC Mutual Fund FAQ assistant.

---

## 1. Architecture Goals & Principles

| Principle | Implication for Design |
|-----------|------------------------|
| **Accuracy over intelligence** | Ground every answer strictly in retrieved corpus chunks; never let the LLM free-generate facts. |
| **Compliance-first** | PII guard and advisory refusal run *before* any retrieval or generation. Guardrails are non-bypassable. |
| **Traceability** | Every chunk carries `source_url` + `scrape_date`; citations and freshness flow from metadata, not the model. |
| **Determinism where possible** | Use regex/rules for PII and hard-format enforcement; reserve the LLM for language understanding and phrasing. |
| **Small, curated corpus** | 20 URLs only — favors high-precision retrieval, allows aggressive chunk quality control. |
| **Stateless single-turn** | Each query is independent (no memory in v1) — simplifies privacy posture and scaling. |
| **Separation of concerns** | Ingestion (offline) is fully decoupled from query serving (online). |

### Non-Functional Targets
| Attribute | Target |
|-----------|--------|
| Response latency (p95) | ≤ 4 s end-to-end (including LLM call) |
| Citation correctness | 100% of answers carry exactly one corpus URL |
| Hallucination rate | ~0% (grounded generation + "I don't know" fallback) |
| PII leakage | 0 (hard regex gate, no echo, no storage) |
| Corpus size | 20 source URLs (15–25 allowed) |
| Availability | Best-effort (prototype); single-region deployment acceptable |

---

## 2. System Overview

The system splits into two decoupled planes:

```
┌──────────────────────────────────────────────────────────────────────┐
│                        OFFLINE INGESTION PLANE                         │
│   (run on a schedule / manually; produces the vector index)           │
│                                                                        │
│   20 URLs ─▶ Scraper ─▶ Cleaner ─▶ Field Extractor ─▶ Chunker ─▶      │
│             Metadata Tagger ─▶ Embedder ─▶ Vector Store (persisted)    │
└──────────────────────────────────────────────────────────────────────┘
                                   │  (persisted index + metadata)
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          ONLINE SERVING PLANE                          │
│                                                                        │
│   UI ─▶ API ─▶ PII Guard ─▶ Classifier ─▶ {Retriever ─▶ Generator}    │
│                                          ─▶ Refusal / Scope responder  │
│                                  ─▶ Response Formatter ─▶ UI           │
└──────────────────────────────────────────────────────────────────────┘
```

- **Ingestion plane** runs offline. It is idempotent and re-runnable; each run stamps chunks with a fresh `scrape_date`.
- **Serving plane** is a stateless request/response pipeline. It reads the persisted vector index but never writes to it.

---

## 3. Component Architecture

### 3.1 Frontend (UI Layer)

| Aspect | Decision |
|--------|----------|
| Framework | React (Vite) or Streamlit for rapid prototype; React recommended for the "full product" deliverable |
| Responsibilities | Render welcome message, 3 example questions, disclaimer banner, input box, formatted response area |
| State | Single-turn; holds current query + latest response only (no chat history persistence in v1) |
| Disclaimer | Always-visible: `"Facts-only. No investment advice."` |
| Rendering | Answer text + clickable citation link + `Last updated from sources: <date>` footer |
| Accessibility | Semantic HTML, keyboard-navigable input, ARIA labels on example-question buttons |

**Required UI elements** (from FR 6.5):
1. Welcome message describing scope (6 HDFC MF schemes, facts-only)
2. Three pre-loaded example questions (clickable to auto-fill):
   - "What is the expense ratio of HDFC Mid Cap Fund?"
   - "What's the lock-in period for HDFC ELSS Tax Saver?"
   - "How to download my capital gains statement?"
3. Visible disclaimer
4. Input field
5. Response area (answer + citation + footer)

### 3.2 Backend API Layer

| Aspect | Decision |
|--------|----------|
| Framework | FastAPI (Python) — async, typed, OpenAPI docs out of the box |
| Primary endpoint | `POST /api/query` → `{ "query": "<text>" }` |
| Response schema | `{ answer, source_url, last_updated, response_type, refused }` |
| Aux endpoints | `GET /api/health`, `GET /api/examples`, `GET /api/meta` (scrape date, scheme list) |
| CORS | Restrict to the frontend origin |
| Rate limiting | Per-IP token bucket (abuse protection); optional for prototype |
| Logging | Log query classification + retrieval scores; **never log raw input that tripped the PII guard** |
| Auth | None for prototype; if exposed publicly, add a simple API key or basic throttle |

> **Security note:** The `/api/query` endpoint is network-exposed and unauthenticated in the prototype. Before any public deployment, add rate limiting and consider an API key, since an open LLM-backed endpoint can be abused for cost or prompt-injection probing.

### 3.3 Guardrail Layer (Pre-Processing)

This layer runs **before** retrieval/generation and is the compliance backbone.

#### Layer 1 — PII Guard (deterministic, regex-based)
| PII Type | Pattern | Notes |
|----------|---------|-------|
| PAN | `[A-Z]{5}[0-9]{4}[A-Z]` | 10-char tax identifier |
| Aadhaar | `\d{4}[\s-]?\d{4}[\s-]?\d{4}` | 12-digit, space/hyphen tolerant |
| Phone | `[6-9]\d{9}` | Indian mobile |
| Email | RFC-ish email regex | Standard |
| Account Number | `\d{8,18}` | Long digit sequences |
| OTP | `\b\d{4,6}\b` in OTP context | Context-gated to reduce false positives |

Behavior on match: **reject immediately**, return the standard PII rejection message, do **not** echo the PII, do **not** store the input, do **not** pass downstream.

#### Layer 2 — Query Classifier (hybrid: rules + LLM)
Routes each clean query into one of three intents:

| Intent | Trigger examples | Downstream path |
|--------|------------------|-----------------|
| `FACTUAL` | "expense ratio of…", "lock-in for…", "who manages…" | → RAG retrieval + generation |
| `ADVISORY` | "should I buy…", "which is better…", "will NAV go up…", "what returns will I get…" | → Safe refusal generator |
| `OUT_OF_SCOPE` | scheme not in corpus, unrelated topic | → Scope boundary responder |

Hybrid strategy:
- **Fast rule pass** first: regex/keyword lists for obvious advisory phrases ("should I", "better", "recommend", "predict", "returns will") and obvious factual data-type keywords. Catches the clear cases cheaply and deterministically.
- **LLM fallback** for ambiguous cases: a small classification prompt returns one label. Default to `FACTUAL` when borderline but answerable (per edge case #4), otherwise clarify.

### 3.4 Retrieval Layer (RAG Core)

```
clean factual query
      │
      ▼
[Embed query]  ──(same model as ingestion)──▶ query vector
      │
      ▼
[Vector similarity search]  top-k (k=4..6) with score threshold
      │
      ├─ scores below threshold ──▶ "I don't have this in my sources" fallback
      │
      ▼
[Optional metadata filter]  by scheme_name / data_type (from classifier hints)
      │
      ▼
[Re-rank / select]  ──▶ top chunks + their metadata (source_url, scrape_date)
```

| Aspect | Decision |
|--------|----------|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` — **runs locally, 100% free, no API key**. Must match ingestion. (`BAAI/bge-small-en-v1.5` is a free higher-quality alternative.) |
| Vector store | ChromaDB (local, persistent) — **free**. FAISS is a free lightweight alternative. No cloud/managed service needed. |
| Top-k | 4–6 chunks |
| Score threshold | Tunable; below threshold → "not in sources" (prevents hallucination, satisfies edge case #8) |
| Metadata filtering | Pre-filter by `scheme_name` / `data_type` when the classifier extracts them, improving precision on the small corpus |
| Citation selection | Pick `source_url` of the highest-scoring chunk that supports the answer |

### 3.5 Generation Layer (LLM)

| Aspect | Decision |
|--------|----------|
| Model | **Groq API free tier** (Llama 3.x — fast, generous free limit). Any instruction-following model works. |
| Mode | Grounded generation only — context = retrieved chunks; **no external knowledge** |
| Output contract | ≤3 sentences, plain language, no opinions/advice/predictions |
| Citation | Injected from chunk metadata (not asked of the model) by the formatter |
| Freshness | `scrape_date` → "Last updated from sources: <date>" appended by the formatter |
| Fallback | If context insufficient → "I don't have this information in my sources." |

**System prompt enforces:**
- Answer ONLY from provided context; if absent, say you don't know.
- Maximum 3 sentences.
- No recommendations, comparisons, predictions, or return calculations.
- Do not invent numbers, dates, or names.

### 3.6 Response Paths (3 branches)

| Path | Produced by | Content |
|------|-------------|---------|
| **Factual answer** | Retriever + Generator + Formatter | ≤3-sentence grounded answer + one corpus citation + last-updated footer |
| **Safe refusal** | Refusal generator | Polite facts-only message + educational link (AMFI/SEBI from corpus) + footer |
| **Scope boundary** | Scope responder | "I cover these 6 HDFC schemes…" + link to hdfcfund.com + footer |

### 3.7 Response Formatter (Post-Processing)
- Enforces the strict output contract regardless of branch.
- **Sentence-count check:** truncate/regenerate if >3 sentences.
- **Citation check:** ensures exactly one URL, and that it belongs to the 20-URL corpus (validated against an allow-list).
- **Footer injection:** appends `Last updated from sources: <date>` using the cited chunk's `scrape_date`.
- **PII echo check:** final scan to guarantee no PII leaks into output.

---

## 4. Ingestion Pipeline (Offline)

```
For each of the 20 URLs:
  1. Fetch        ── HTML pages via requests/Playwright; PDFs via pdf loader
  2. Clean        ── strip nav/ads/boilerplate; normalize whitespace & ₹/% symbols
  3. Extract      ── pull structured fields (expense ratio, exit load, SIP, manager…)
  4. Chunk        ── RecursiveCharacterTextSplitter (size ~500–800 tokens, overlap ~80)
  5. Tag metadata ── attach the chunk metadata schema (below)
  6. Embed        ── vectorize each chunk
  7. Upsert       ── write vectors + metadata into the vector store (persisted)
```

| Step | Tooling |
|------|---------|
| Scraper / loader | BeautifulSoup + requests (static), Playwright (JS-heavy Groww pages), PDF loader for factsheets/KIM/SID |
| Cleaner | Custom Python (boilerplate removal, Unicode/₹ normalization) |
| Field extractor | Targeted parsers for Groww scheme-page data points |
| Chunker | LangChain `RecursiveCharacterTextSplitter` |
| Embedder | Same model as query-time embedding (critical for vector-space consistency) |

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

This metadata powers: accurate citation (`source_url`), freshness (`scrape_date`), source prioritization (`source_type`), and query routing / metadata filtering (`data_type`, `scheme_name`).

### Ingestion Considerations
- **Idempotent re-runs:** a full re-scrape replaces the index and refreshes `scrape_date`.
- **JS rendering:** Groww pages may require Playwright (rendered DOM) rather than raw HTML.
- **PDF freshness:** factsheets/KIM/SID change monthly — document a refresh cadence.
- **Corpus allow-list:** the 20 URLs are the *only* permitted sources; the citation validator enforces this at serve time.

---

## 5. End-to-End Request Flow

```
1. User submits query in UI
2. POST /api/query
3. PII Guard (regex)
     ├─ PII found ─▶ return PII rejection (no echo, no store) ─▶ STOP
     └─ clean ─▶ continue
4. Query Classifier (rules → LLM fallback)
     ├─ ADVISORY      ─▶ Safe refusal + educational link ─▶ format ─▶ return
     ├─ OUT_OF_SCOPE  ─▶ Scope boundary + AMC link ─▶ format ─▶ return
     └─ FACTUAL       ─▶ continue
5. Embed query ─▶ vector search (top-k, threshold, optional metadata filter)
     ├─ no chunk above threshold ─▶ "not in my sources" ─▶ format ─▶ return
     └─ chunks found ─▶ continue
6. LLM grounded generation (context = retrieved chunks)
7. Response Formatter
     ├─ enforce ≤3 sentences
     ├─ validate single citation ∈ corpus allow-list
     ├─ append "Last updated from sources: <scrape_date>"
     └─ final PII-echo scan
8. Return formatted response ─▶ UI renders answer + link + footer
```

---

## 6. Technology Stack (Recommended)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | React (Vite) — or Streamlit (also free) | Meets "full product" frontend deliverable; clean component model |
| Backend | FastAPI (Python) | Async, typed, auto OpenAPI, strong RAG ecosystem; **free, open-source** |
| RAG framework | LangChain | Loaders, splitters, retriever abstractions; **free, open-source** |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local) | **Free, no API key, runs on CPU**; no per-call cost |
| Vector store | ChromaDB (persistent) or FAISS | **Free, local, file-based**; no managed-service bill |
| LLM | Groq free tier | **$0** — generous free API limits |
| Scraping | requests + BeautifulSoup + Playwright | **Free, open-source**; static + JS-rendered pages |
| PDF parsing | pypdf / pdfplumber | **Free, open-source**; factsheets, KIM, SID |
| Config/secrets | `.env` + environment variables | Keep API keys out of source |

> **Cost posture:** Every component above is free. The embedding model and vector store run locally with no API calls. The only external dependency is the LLM — Groq's free-tier API (no cost).
>
> Choices are deliberately swappable. The architecture only requires that the *query-time* embedding model matches the *ingestion-time* model.

### 6.1 Total Cost Breakdown ($0)

| Component | Service | Cost | Notes |
|-----------|---------|------|-------|
| Scraping/parsing | requests, BeautifulSoup, Playwright, pypdf | **$0** | Open-source libraries |
| Embeddings | sentence-transformers (local) | **$0** | Runs on CPU, no API key |
| Vector store | ChromaDB / FAISS (local file) | **$0** | No managed DB |
| LLM | Groq free tier | **$0** | Free API limits |
| Backend | FastAPI | **$0** | Open-source |
| Frontend | React (Vite) / Streamlit | **$0** | Open-source |
| Hosting | HF Spaces / Streamlit Cloud / Render / Vercel | **$0** | Free tiers; no card needed |
| **Total** | | **$0 / month** | No credit card required anywhere |

**Free LLM access notes:**
- **Groq** — sign up free, get an API key, generous free rate limits, very fast (Llama 3.x).

---

## 7. Data & Configuration Management

| Item | Approach |
|------|----------|
| Corpus URL allow-list | Single source-of-truth config (e.g., `sources.json`) used by both ingestion and the citation validator |
| Secrets (LLM/API keys) | Environment variables / `.env` (git-ignored); never committed |
| Vector index | Persisted to local disk (Chroma/FAISS) — **free, no managed service**; rebuilt by re-running ingestion |
| Scrape date | Stamped per chunk at ingestion; surfaced in every response footer |
| Scheme registry | Canonical list of the 6 schemes + aliases for matching ("HDFC Equity Fund" ↔ Flexi Cap) |

---

## 8. Compliance & Safety Mapping

| Constraint (from context) | Architectural enforcement point |
|---------------------------|--------------------------------|
| No PII collection/storage/echo | Layer 1 PII Guard + final echo scan; no logging of flagged inputs |
| Citations only from 20 URLs | Citation validator against corpus allow-list in Formatter |
| No advisory/opinion/predictions | Classifier → refusal branch + system-prompt prohibitions |
| ≤3 sentences | Formatter sentence-count enforcement |
| One citation + last-updated footer always | Formatter mandatory injection |
| No hallucination | Score threshold + grounded prompt + "I don't know" fallback |
| Direct-plan-only scope | Scope responder + welcome-message disclaimer |
| Official sources only | Ingestion allow-list (no third-party blogs) |

---

## 9. Error Handling & Fallbacks

| Failure | Behavior |
|---------|----------|
| LLM API error/timeout | Return graceful error; suggest retry; never fabricate an answer |
| No chunk above threshold | "I don't have this information in my sources." + footer |
| Ambiguous query | Default to factual if answerable; else ask a short clarifying question |
| Two schemes in one query | Answer both if both have clear chunks; else clarify |
| Non-English query | Answer in English or state language limitation |
| Vector store unavailable | Health check fails; API returns 503; UI shows friendly downtime message |

---

## 10. Deployment Topology

```
┌─────────────┐      HTTPS       ┌──────────────────┐
│   Browser   │ ───────────────▶ │  Frontend (free   │
│   (React)   │                  │  static hosting)  │
└─────────────┘                  └────────┬──────────┘
                                          │ /api/*
                                          ▼
                                 ┌──────────────────┐
                                 │  FastAPI backend  │
                                 │  (free container) │
                                 └───┬───────────┬───┘
                                     │           │
                          persisted  │           │  HTTPS (free tier)
                          read-only  ▼           ▼
                          ┌────────────────┐  ┌───────────────────┐
                          │  Vector store  │  │  LLM (free):       │
                          │  Chroma/FAISS  │  │  Groq free tier    │
                          │  (local file)  │  │                    │
                          └────────────────┘  └───────────────────┘
```

### Free Hosting Options (pick one)
| Need | Free option |
|------|-------------|
| All-in-one (UI + API + index) | **Hugging Face Spaces** (free) — Streamlit/Gradio app, or Docker Space |
| Streamlit UI | **Streamlit Community Cloud** (free) |
| FastAPI backend | **Render** free web service, or **Railway**/**Fly.io** free allowance |
| React/static frontend | **Vercel** / **Netlify** / **GitHub Pages** (free) |
| Fully local demo | Run `uvicorn` + frontend on your laptop; record the ≤3-min demo video |

> **Zero-cost path:** Hugging Face Spaces (free) hosting a Streamlit app that bundles the FastAPI logic + local Chroma index, calling Groq's free-tier LLM API. No credit card required.

- **Prototype:** single free Space/container running the app + bundled Chroma index. A ≤3-min demo video or live link satisfies the prototype deliverable.
- **GitHub push:** performed by the user (not the AI), per the submission rule.
- **Scaling (future):** stateless API scales horizontally; the local vector store is more than enough for a 20-URL corpus, so no paid vector DB is ever required.

---

## 11. Suggested Repository Structure

```
mutual-fund-faq-chatbot/
├── README.md                    # all required sections (source list, sample Q&A, disclaimer)
├── Docs/
│   ├── context.md
│   └── architecture.md
├── data/
│   ├── sources.json             # 20-URL allow-list (single source of truth)
│   └── chroma/                  # persisted vector index (generated)
├── ingestion/
│   ├── scrape.py                # fetch HTML/PDF
│   ├── clean.py                 # normalize + boilerplate removal
│   ├── extract.py               # structured field extraction
│   ├── chunk_embed.py           # split, tag metadata, embed, upsert
│   └── run_ingest.py            # orchestrates the offline pipeline
├── backend/
│   ├── main.py                  # FastAPI app + routes
│   ├── guardrails/
│   │   ├── pii.py               # Layer 1 regex guard
│   │   └── classifier.py        # Layer 2 hybrid intent routing
│   ├── rag/
│   │   ├── retriever.py         # embed + vector search + filter
│   │   └── generator.py         # grounded LLM generation
│   ├── responders/
│   │   ├── refusal.py           # advisory safe refusal
│   │   └── scope.py             # out-of-scope boundary
│   ├── formatter.py             # ≤3 sentences, citation + footer enforcement
│   └── config.py                # env, model names, thresholds
├── frontend/
│   └── (React app: welcome, examples, disclaimer, input, response area)
├── tests/
│   ├── test_pii.py              # PAN/Aadhaar/phone/email/OTP detection
│   ├── test_classifier.py       # factual vs advisory vs out-of-scope
│   ├── test_format.py           # sentence count, single citation, footer
│   └── test_retrieval.py        # right scheme + right data type
├── .env.example
└── requirements.txt
```

---

## 12. Testing Strategy (maps to Success Criteria)

| Test area | What it verifies | Linked criterion |
|-----------|------------------|------------------|
| PII detection | All 6 PII types rejected, no echo | #5 |
| Classifier | 6 advisory types refused; 17 factual types routed correctly | #2, #4 |
| Retrieval | Correct scheme + data type chunk returned | #1 |
| Grounding | Answer faithful to chunk; unknown → "I don't know" | #14 |
| Format | ≤3 sentences, one citation, footer present | #3, #6, #7 |
| Citation validity | URL ∈ 20-URL corpus and resolves | #3, #9, #10 |
| ELSS lock-in | Returns "3 years" | #11 |
| Statement/CAS | Process + correct guide link | #12 |
| Educational | "What is a mutual fund?" answered from AMFI/SEBI | #13 |
| UI | Welcome + 3 examples + disclaimer visible | #8 |

---

## 13. Known Architectural Limitations

| Limitation | Architectural impact | Mitigation |
|------------|----------------------|------------|
| 20-URL corpus | Cannot answer beyond curated scope | Scope responder + UI scope note |
| Freshness = scrape date | Numbers (NAV, AUM, expense ratio) may drift | `scrape_date` footer + re-ingestion |
| Direct plans only | No Regular/IDCW data | Scope responder + AMC link |
| English only | No regional-language understanding | Language-limit message |
| Single-turn | No conversation memory | Each request independent (privacy benefit) |
| Groww vs AMC lag | Minor discrepancies | Always cite source + show date |
| PDF staleness | Factsheets change monthly | Documented refresh cadence |

---

*Source of truth: `Docs/context.md` (derived from Problem Statement v4.0). Technology choices are recommendations; the guardrail ordering, grounded-generation contract, and citation/freshness enforcement are the non-negotiable architectural invariants.*
