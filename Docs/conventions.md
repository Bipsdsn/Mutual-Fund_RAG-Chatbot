# Conventions: RAG-Based Mutual Fund FAQ Chatbot

> **The highest-leverage file. Re-read it constantly before writing or editing code.**
> Every contributor (human or AI) follows these rules so the codebase stays consistent, compliant, and easy to reason about.
> Derived from `context.md`, `architecture.md`, `data-flow-architecture.md`, `implementation-plan.md`, `edgecases.md`, and the Problem Statement.

> **Stack (locked):** FastAPI · LangChain · local `sentence-transformers/all-MiniLM-L6-v2` · local ChromaDB · **Groq** LLM · React (Vite) or Streamlit UI. **Cost: $0.** No paid services.

---

## 0. The Ten Non-Negotiables (memorize these)

1. **Never let the LLM invent facts.** Answers come only from retrieved corpus chunks. No context → "I don't have this information in my sources."
2. **Citations come from metadata, never from the model.** Exactly one URL, always from the 20-URL allow-list.
3. **PII guard runs first, always.** Never echo, never store, never log raw PII.
4. **Every answer: ≤3 sentences + one citation + freshness footer.** Enforced in the Formatter, not trusted to the LLM.
5. **No advice/opinion/prediction/return-calc — ever.** Classifier routes these to a refusal.
6. **The Formatter is the single output gate.** All branches pass through it.
7. **Ingestion writes the index; serving only reads it.** Never write to the vector store at query time.
8. **Secrets live in `.env` only.** Never hardcode or commit `GROQ_API_KEY`.
9. **Same embedding model at ingest and query time.** Mismatch = silent retrieval failure.
10. **The AI never runs `git push`.** The user owns all git history operations.

---

## 1. Folder Structure (authoritative)

```
mutual-fund-faq-chatbot/
├── README.md                    # required sections (source list, sample Q&A, disclaimer)
├── requirements.txt             # pinned versions
├── .env.example                 # keys & tunables (no real secrets)
├── .gitignore                   # .venv, .env, data/chroma/, __pycache__, node_modules
├── Docs/                        # all design docs (this file lives here)
├── data/
│   ├── sources.json             # 20-URL allow-list — SINGLE SOURCE OF TRUTH
│   ├── schemes.json             # canonical scheme names + aliases
│   ├── raw_cache/               # dev-only cached raw HTML/PDF (git-ignored)
│   └── chroma/                  # persisted vector index (generated, git-ignored)
├── ingestion/                   # OFFLINE write-path (never imported by serving)
│   ├── scrape.py
│   ├── clean.py
│   ├── extract.py
│   ├── chunk_embed.py
│   └── run_ingest.py
├── backend/                     # ONLINE read-path
│   ├── main.py                  # FastAPI app + routes ONLY (thin)
│   ├── config.py                # env loading; the only place os.environ is read
│   ├── corpus.py                # loads sources.json → ALLOWED_URLS, scheme registry
│   ├── models.py                # Pydantic request/response models
│   ├── guardrails/
│   │   ├── pii.py
│   │   └── classifier.py
│   ├── rag/
│   │   ├── retriever.py
│   │   └── generator.py
│   ├── responders/
│   │   ├── refusal.py
│   │   └── scope.py
│   └── formatter.py
├── frontend/                    # React (Vite) or Streamlit
└── tests/
    ├── test_pii.py
    ├── test_classifier.py
    ├── test_retrieval.py
    └── test_format.py
```

**Rules:**
- `ingestion/` and `backend/` must **not** import from each other. Their only shared contract is the persisted Chroma index + `data/*.json`.
- `backend/main.py` stays thin: parse request → call pipeline functions → return. No business logic inline.
- `config.py` is the **only** module that reads `os.environ`. Everything else imports from it.
- Generated artifacts (`data/chroma/`, `data/raw_cache/`) are git-ignored, never committed.

---

## 2. Naming Conventions

### 2.1 Python

| Element | Convention | Example |
|---------|-----------|---------|
| Modules / files | `snake_case.py` | `pii.py`, `chunk_embed.py` |
| Functions / variables | `snake_case` | `retrieve_chunks`, `best_score` |
| Classes / Pydantic models | `PascalCase` | `QueryRequest`, `ChunkRecord` |
| Constants | `UPPER_SNAKE_CASE` | `ALLOWED_URLS`, `SCORE_THRESHOLD`, `MAX_SENTENCES` |
| Enums | `PascalCase` name, `UPPER_SNAKE` members | `ResponseType.PII_REJECTED` |
| Private helpers | leading underscore | `_normalize_whitespace` |
| Booleans | `is_` / `has_` / `should_` prefix | `is_advisory`, `has_pii` |

### 2.2 Domain vocabulary (use these exact terms everywhere)

| Term | Meaning | Do NOT call it |
|------|---------|----------------|
| `source_url` | The one citation URL | `link`, `ref`, `url` (ambiguous) |
| `scrape_date` | Ingestion date → freshness footer | `date`, `timestamp` |
| `scheme_name` | Canonical fund name | `fund`, `name` |
| `data_type` | expense_ratio / exit_load / … | `category` (that's `scheme_category`) |
| `response_type` | FACTUAL / ADVISORY_REFUSAL / OUT_OF_SCOPE / NO_SOURCE / PII_REJECTED | `status`, `kind` |
| `chunk` | A retrievable text unit + metadata | `doc`, `passage` |
| `guardrail` | PII guard or classifier | `filter`, `middleware` |

### 2.3 `response_type` enum (canonical values — never free-string these)

```
FACTUAL            # grounded answer returned
ADVISORY_REFUSAL   # advice/opinion/prediction refused
OUT_OF_SCOPE       # scheme/topic not covered
NO_SOURCE          # factual but not found in corpus ("I don't know")
PII_REJECTED       # PII detected, short-circuited
```

### 2.4 Frontend (React)

| Element | Convention | Example |
|---------|-----------|---------|
| Components | `PascalCase.jsx` | `AnswerCard.jsx`, `DisclaimerBanner.jsx` |
| Hooks | `useCamelCase` | `useQuery` |
| Non-component files | `camelCase.js` | `api.js` |
| CSS classes | `kebab-case` | `answer-card`, `citation-link` |

### 2.5 `data_type` allowed values (closed set — matches metadata schema)

```
expense_ratio | exit_load | sip_details | lumpsum | risk | benchmark |
fund_manager | tax | lock_in | aum | nav | sebi_category |
statement_guide | investor_education | scheme_facts
```
If a new type is needed, add it here AND in `data-flow-architecture.md` §3.3 before using it.

---

## 3. Configuration & Secrets

- **All** tunables come from `config.py`, which loads `.env` via `python-dotenv`.
- Required env keys (see `.env.example`):
  ```
  GROQ_API_KEY=                 # secret — never commit
  GROQ_MODEL=llama-3.1-8b-instant
  EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
  CHROMA_DIR=./data/chroma
  TOP_K=5
  SCORE_THRESHOLD=0.35          # tune in Phase 3
  MAX_SENTENCES=3
  ALLOWED_ORIGINS=http://localhost:5173
  ```
- `config.py` **fails fast** if `GROQ_API_KEY` is missing — raise a clear `RuntimeError` at startup, do not limp along (see edge case SYS-3).
- Never read `os.environ` outside `config.py`. Import typed values:
  ```python
  from backend.config import settings
  settings.top_k          # int
  settings.score_threshold  # float
  ```

---

## 4. Error Handling Patterns

### 4.1 Golden rule
**Fail safe, never fabricate.** Any failure on the factual path degrades to a compliant fallback message — never to a guessed answer.

### 4.2 Result-style returns over exceptions for control flow
Guardrail and pipeline steps return typed results, not exceptions, for *expected* outcomes:

```python
# GOOD — expected outcomes are values, not exceptions
@dataclass
class PIIResult:
    has_pii: bool
    pii_types: list[str]          # names only, NEVER the matched values

@dataclass
class RetrievalResult:
    chunks: list[Chunk]
    best_score: float
    has_match: bool               # best_score >= SCORE_THRESHOLD
```

Reserve `raise` for **programmer errors / misconfig** (missing key, corrupt index), not for user-input branches.

### 4.3 Per-layer behavior (must match edgecases.md & architecture §9)

| Layer | On failure | Returns |
|-------|-----------|---------|
| PII guard | match found | `PII_REJECTED` standard message; stop pipeline |
| Classifier | LLM fallback errors | default to `FACTUAL` if answerable, else clarify; never crash |
| Retriever | below threshold | `NO_SOURCE` → "I don't have this in my sources." |
| Generator | Groq timeout/5xx/rate-limit | graceful retry message; **never** fabricate |
| Formatter | bad citation / >3 sentences | repair (truncate / force single citation) or fall back to `NO_SOURCE` |
| Index load | missing/corrupt | `/api/health` → unhealthy; `/api/query` → 503 |

### 4.4 Groq call wrapper (single choke point)
All Groq calls go through **one** helper in `generator.py` (and a thin reuse in `classifier.py`):
```python
def call_groq(system: str, user: str, *, max_tokens: int, temperature: float = 0.0) -> str:
    # timeout, 1–2 retries with backoff, structured logging of latency only
    # on persistent failure: raise GroqUnavailable -> caller returns graceful message
```
- `temperature=0.0` for determinism (facts, not creativity).
- Keep prompts short to respect free-tier limits (edge case SYS-2).
- Never pass raw user PII to Groq — PII guard runs before any Groq call.

### 4.5 HTTP status codes (API)

| Situation | Status |
|-----------|--------|
| Normal answer / refusal / scope / no-source / PII-rejected | `200` (the *content* signals the outcome via `response_type`) |
| Malformed request body | `422` (FastAPI/Pydantic default) |
| Index unavailable / not loaded | `503` |
| Unhandled server error | `500` (generic message; no stack trace to client) |

> Note: PII rejection and refusals are **200**, not 4xx — they are valid, expected responses with a compliant body.

### 4.6 Logging rules
- Log: `response_type`, classification label, retrieval `best_score`, latency.
- **Never log:** raw query text that tripped the PII guard, matched PII values, or full user inputs containing potential PII.
- Use Python `logging` (not `print`) in `backend/`. `print` is acceptable only in `ingestion/` CLI scripts for progress.

---

## 5. Libraries to Use (and how)

| Need | Use | Notes / how |
|------|-----|-------------|
| API | `fastapi` + `uvicorn[standard]` | async routes; Pydantic models in `models.py` |
| Validation | `pydantic` v2 | all request/response shapes are models |
| RAG glue | `langchain`, `langchain-community`, `langchain-text-splitters` | `RecursiveCharacterTextSplitter` for chunking |
| Embeddings | `sentence-transformers` | load `all-MiniLM-L6-v2` once at module load; reuse |
| Vector store | `chromadb` (persistent client) | `PersistentClient(path=CHROMA_DIR)` |
| LLM | `groq` SDK (or `langchain-groq`) | single wrapper; `temperature=0` |
| Static scrape | `requests` + `beautifulsoup4` | set a User-Agent; timeouts always |
| JS scrape | `playwright` | only for Groww `html_js` pages; reuse one browser context |
| PDF | `pypdf` (text) / `pdfplumber` (tables) | factsheets/KIM/SID |
| Env | `python-dotenv` | loaded once in `config.py` |
| Tests | `pytest` + `httpx` | `httpx` for FastAPI `TestClient`-style calls |

**Library rules:**
- Pin versions in `requirements.txt` (reproducibility; edge case + DoD).
- Load heavy models (embedding model, Chroma client) **once** at module import / app startup — never per request.
- Do not add a new dependency without updating `requirements.txt` and noting why. Prefer stdlib where reasonable.
- No paid SDKs (OpenAI, Pinecone, etc.). If you reach for one, stop — it violates the $0 constraint.

---

## 6. Code Patterns to Follow

### 6.1 Pipeline = pure-ish functions
Each stage is a function with explicit inputs/outputs. The orchestrator in `main.py` wires them:
```python
def handle_query(query: str) -> QueryResponse:
    pii = scan_pii(query)
    if pii.has_pii:
        return format_response(pii_rejection(), ResponseType.PII_REJECTED)

    intent = classify(query)
    if intent.label == "ADVISORY":
        return format_response(refusal_for(intent), ResponseType.ADVISORY_REFUSAL)
    if intent.label == "OUT_OF_SCOPE":
        return format_response(scope_message(), ResponseType.OUT_OF_SCOPE)

    result = retrieve(query, hints=intent.hints)
    if not result.has_match:
        return format_response(no_source_message(), ResponseType.NO_SOURCE)

    draft = generate(query, result.chunks)
    return format_response(draft, ResponseType.FACTUAL, citation=result.citation,
                           scrape_date=result.scrape_date)
```
- **Every return goes through `format_response`** (the single output gate).
- Branch order is fixed: **PII → classify → retrieve → generate → format.** Never reorder.

### 6.2 Metadata-driven citation & freshness
Citation and footer are derived from chunk metadata in the Formatter — never asked of the LLM:
```python
# GOOD
citation = result.citation                 # from chunk metadata
footer = f"Last updated from sources: {result.scrape_date}"

# BAD — do not ask the model for the URL or date
```

### 6.3 PII names, not values
When reporting PII detection, store/return **type names only**:
```python
return PIIResult(has_pii=True, pii_types=["PAN"])   # never the matched string
```

### 6.4 Constants over magic values
```python
# GOOD
if result.best_score < settings.score_threshold: ...
# BAD
if result.best_score < 0.35: ...
```

### 6.5 Type hints everywhere
All functions in `backend/` are fully type-hinted. Pydantic models for any data crossing the API boundary.

### 6.6 Docstrings on public functions
One-line purpose + which edge cases / SC it covers, e.g. `"""Reject PII before any processing (SC5, edge cases PII-1..11)."""`

---

## 7. Patterns to Avoid (anti-patterns)

| ❌ Anti-pattern | ✅ Instead |
|----------------|-----------|
| Asking the LLM to "include the source URL" | Inject `source_url` from metadata in Formatter |
| Asking the LLM to "keep it under 3 sentences" and trusting it | Prompt for brevity **and** enforce in Formatter |
| Letting the LLM answer from general knowledge | Grounded-only prompt + threshold + NO_SOURCE fallback |
| Skipping the PII guard "just for this path" | PII guard is unconditional and first |
| Reordering branches (retrieve before classify) | Fixed order: PII → classify → retrieve → generate → format |
| Reading `os.environ` in random modules | Only `config.py` reads env |
| Hardcoding the 20 URLs in code | Load from `data/sources.json` |
| Writing to Chroma during a query | Serving is read-only; only ingestion writes |
| Re-loading the embedding model per request | Load once at startup |
| Logging the raw query on PII rejection | Log `response_type` only |
| Catching `Exception: pass` (silent failures) | Catch specific errors; degrade to a compliant fallback |
| Returning 4xx for refusals/PII | Return 200 with a compliant body + `response_type` |
| Different embedding models for ingest vs query | Assert identical `EMBEDDING_MODEL` |
| `print()` for backend logging | Use `logging` |
| Committing `.env`, `data/chroma/`, or cached HTML | `.gitignore` them |
| Adding a paid API "to make it better" | Violates $0 constraint — stop |
| Multi-turn memory / storing queries | Single-turn, stateless, no persistence |
| Fabricating a citation when unsure | Fall back to NO_SOURCE |
| AI running `git push` / `git commit` | User owns git operations |

---

## 8. Prompting Conventions (Groq)

- **System prompt is the contract.** It must state: answer only from provided context; if absent say you don't know; max 3 sentences; no advice/opinions/predictions/returns; do not invent numbers, dates, names.
- **Context block is explicit and delimited** (e.g., fenced with clear markers) so the model can't confuse instructions with data — treat retrieved text as untrusted data, not instructions (defends prompt injection, ADV-10).
- **`temperature=0.0`** for factual generation and classification.
- **No few-shot examples that contain advice** — examples must model refusals and grounded answers only.
- **Classifier prompt returns a single token/label** from the closed set; parse strictly, default to `FACTUAL`-if-answerable on parse failure.
- Keep prompts short (free-tier token budget).

---

## 9. Compliance Invariants in Code (assert these)

These map to `edgecases.md` §1.9. Where cheap, assert them in the Formatter and in tests:

| Invariant | Enforcement |
|-----------|-------------|
| Exactly one citation ∈ `ALLOWED_URLS` | Formatter validates against `corpus.ALLOWED_URLS` |
| ≤ `MAX_SENTENCES` sentences | Formatter counts and trims |
| Footer always present | Formatter appends unconditionally |
| No PII in output | Formatter final scan |
| No advice on any path | Classifier + system prompt |
| No source outside 20 URLs | Ingestion allow-list + Formatter validator |
| Unknown → explicit "I don't know" | Retriever threshold + Generator fallback |

---

## 10. Testing Conventions

- Test files mirror modules: `test_pii.py`, `test_classifier.py`, `test_retrieval.py`, `test_format.py`.
- Each test references the edge-case ID and/or SC it covers in its name or docstring:
  ```python
  def test_pan_rejected_no_echo():
      """PII-1 / SC5: PAN rejected, value never echoed."""
  ```
- Guardrail and formatter tests must **not** call Groq (mock or use deterministic paths) so they run offline and fast.
- Retrieval tests assert **scheme + data_type** correctness, not exact wording.
- When a `Discovered During Build` edge case recurs, add a regression test and link it in `edgecases.md`.
- Run `pytest` before considering any phase done (implementation-plan DoD).

---

## 11. Git & Workflow Conventions

- **The AI never runs `git push`, `git commit`, or history-altering commands.** The user performs all git operations.
- Commit messages (when the user commits): imperative mood, scoped — e.g., `ingestion: add Playwright fetch for Groww pages`.
- Never commit: `.env`, `data/chroma/`, `data/raw_cache/`, `node_modules/`, `__pycache__/`.
- Keep `requirements.txt` updated in the same change that adds an import.
- Docs in `Docs/` are the source of truth; if code diverges from a doc, update the doc in the same change.

---

## 12. Quick Reference Card

```
ORDER:        PII → classify → retrieve → generate → FORMAT (always last)
OUTPUT:       ≤3 sentences + 1 corpus citation + "Last updated from sources: <date>"
NO CONTEXT:   "I don't have this information in my sources."
ADVISORY:     polite refusal + AMFI/SEBI educational link + footer
OUT OF SCOPE: list 6 schemes + hdfcfund.com + footer
PII:          reject, no echo, no store, no log; 200 + PII_REJECTED
SECRETS:      .env only; config.py reads env; never commit keys
EMBEDDINGS:   all-MiniLM-L6-v2, same at ingest & query, loaded once
LLM:          Groq, temperature 0, single wrapper, short prompts
COST:         $0 — no paid services, ever
GIT:          user pushes, not the AI
```

---

*Living conventions. If a rule here conflicts with another doc, this file wins for *how to build*; `context.md` wins for *what to build*. Update this file whenever a new convention is agreed.*
