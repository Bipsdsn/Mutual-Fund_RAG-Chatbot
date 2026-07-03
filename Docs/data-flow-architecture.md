# Data-Flow Architecture: RAG-Based Mutual Fund FAQ Chatbot

> Companion to `Docs/architecture.md` and `Docs/context.md`.
> This document focuses **exclusively on how data moves** through the system — from raw source URLs to a rendered, compliant answer. Every stage shows its inputs, transformations, outputs, and the data contracts between components. All diagrams use Mermaid.
>
> **Cost posture:** 100% free stack — local `sentence-transformers` embeddings, local ChromaDB/FAISS, and the Groq free-tier LLM API. No paid service appears in any data path.

---

## 1. Legend & Conventions

```mermaid
flowchart LR
    A[Process / Component]:::proc
    B[(Data Store)]:::store
    C{{Decision}}:::dec
    D[/External Source/]:::ext
    E([Terminal / Response]):::term

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef store fill:#fff2cc,stroke:#d6a700,color:#5c4500
    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

| Symbol | Meaning |
|--------|---------|
| Blue rectangle | Processing component (transforms data) |
| Yellow cylinder | Persistent data store |
| Red diamond | Decision / branch point |
| Green parallelogram | External data source (web/PDF/LLM API) |
| Purple stadium | Terminal output returned to the user |

Two planes carry data:
- **Ingestion plane (offline, write-path):** URLs → vector index. Runs occasionally.
- **Serving plane (online, read-path):** user query → answer. Runs per request, read-only against the index.

---

## 2. Top-Level Data Context (C4-style)

```mermaid
flowchart TB
    user[/End User — Browser/]:::ext

    subgraph SERVE[Serving Plane online, read-only]
        ui[Frontend UI<br/>React/Streamlit]:::proc
        api[FastAPI Backend<br/>POST /api/query]:::proc
        guard[Guardrails<br/>PII + Classifier]:::proc
        rag[RAG Core<br/>Retriever + Generator]:::proc
        fmt[Response Formatter]:::proc
    end

    subgraph INGEST[Ingestion Plane offline, write-path]
        scr[Scraper/Loader]:::proc
        cln[Cleaner]:::proc
        ext2[Field Extractor]:::proc
        chk[Chunker + Tagger]:::proc
        emb[Embedder]:::proc
    end

    subgraph STORES[Persistent Data]
        idx[(Vector Index<br/>Chroma/FAISS<br/>+ metadata)]:::store
        cfg[(sources.json<br/>20-URL allow-list)]:::store
    end

    web[/20 Official URLs<br/>Groww/AMC/SEBI/AMFI/]:::ext
    llm[/Groq LLM<br/>free tier/]:::ext

    user <--> ui <--> api
    api --> guard --> rag --> fmt --> api
    rag <-->|read embeddings + metadata| idx
    rag <-->|grounded prompt| llm
    guard <-->|classify ambiguous| llm

    web --> scr --> cln --> ext2 --> chk --> emb -->|write vectors| idx
    cfg -.allow-list.-> scr
    cfg -.validate citation.-> fmt

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef store fill:#fff2cc,stroke:#d6a700,color:#5c4500
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
```

**Key data boundary:** the Vector Index is the *only* shared state between the two planes. Ingestion **writes** it; serving **reads** it. They never run in the same request.

---

## 3. Ingestion Plane — Detailed Data Flow

### 3.1 Stage-by-stage pipeline

```mermaid
flowchart TD
    start([Run ingestion]):::term
    cfg[(sources.json<br/>20 URLs + source_type + scheme_name)]:::store
    start --> loadcfg[Load allow-list]:::proc
    loadcfg --> cfg
    cfg --> loop{{For each URL}}:::dec

    loop -->|HTML| fetchH[Fetch HTML<br/>requests / Playwright]:::proc
    loop -->|PDF| fetchP[Fetch PDF<br/>pypdf / pdfplumber]:::proc

    fetchH --> raw[/Raw HTML DOM/]:::ext
    fetchP --> rawpdf[/Raw PDF bytes/]:::ext

    raw --> clean[Clean<br/>strip nav/ads/boilerplate<br/>normalize whitespace, ₹, %]:::proc
    rawpdf --> clean

    clean --> norm[Normalized plain text]:::proc
    norm --> extract[Field Extractor<br/>expense ratio, exit load,<br/>SIP, manager, AUM, lock-in...]:::proc
    extract --> structured[Structured fields + clean text]:::proc

    structured --> split[Chunker<br/>RecursiveCharacterTextSplitter<br/>~500-800 tokens, ~80 overlap]:::proc
    split --> chunks[Chunk list]:::proc

    chunks --> tag[Metadata Tagger<br/>attach schema fields]:::proc
    tag --> tagged[Tagged chunks]:::proc

    tagged --> embed[Embedder<br/>all-MiniLM-L6-v2 local]:::proc
    embed --> vectors[Chunk + vector + metadata]:::proc

    vectors --> upsert[Upsert into store]:::proc
    upsert --> idx[(Vector Index<br/>persisted to disk)]:::store
    upsert --> more{{More URLs?}}:::dec
    more -->|yes| loop
    more -->|no| done([Index ready<br/>scrape_date stamped]):::term

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef store fill:#fff2cc,stroke:#d6a700,color:#5c4500
    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

### 3.2 Data transformation table (what each stage produces)

| Stage | Input | Transformation | Output | Free tooling |
|-------|-------|----------------|--------|--------------|
| Load allow-list | `sources.json` | Parse 20 entries (url, source_type, scheme_name, category) | URL work-queue | json (stdlib) |
| Fetch | URL | HTTP GET / headless render / PDF read | Raw HTML or PDF text | requests, Playwright, pypdf |
| Clean | Raw markup | Remove nav/ads/scripts; normalize Unicode, ₹, % | Plain normalized text | BeautifulSoup, custom |
| Extract | Plain text | Regex/selectors pull structured data points | Field dict + body text | custom Python |
| Chunk | Text + fields | Split with overlap, keep semantic boundaries | List of text chunks | LangChain splitter |
| Tag | Chunks | Attach metadata schema (below) | Tagged chunks | custom |
| Embed | Chunk text | Encode to dense vector (384-dim for MiniLM) | `(text, vector, metadata)` | sentence-transformers |
| Upsert | Vector records | Write to Chroma/FAISS, persist to disk | Vector index files | ChromaDB / FAISS |

### 3.3 Chunk record — the core data contract

```mermaid
classDiagram
    class ChunkRecord {
        +string id
        +string text
        +float[] embedding  // 384-dim, MiniLM-L6-v2
        +Metadata metadata
    }
    class Metadata {
        +string source_url
        +string source_type  // groww_scheme_page | amc_official | sebi | amfi
        +string scheme_name
        +string scheme_category
        +string data_type    // expense_ratio | exit_load | sip_details | risk | benchmark | fund_manager | tax | statement_guide | investor_education
        +string scrape_date  // ISO date, drives freshness footer
        +int chunk_index
    }
    ChunkRecord "1" --> "1" Metadata : carries
```

```json
{
  "id": "groww_midcap_0007",
  "text": "The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.74% ...",
  "embedding": [0.0123, -0.0456, "... 384 dims ..."],
  "metadata": {
    "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "source_type": "groww_scheme_page",
    "scheme_name": "HDFC Mid Cap Fund Direct Growth",
    "scheme_category": "Equity — Mid Cap",
    "data_type": "expense_ratio",
    "scrape_date": "2026-06-23",
    "chunk_index": 7
  }
}
```

> **Why this matters downstream:** `source_url` → citation, `scrape_date` → freshness footer, `data_type` + `scheme_name` → metadata pre-filtering at retrieval, `source_type` → ranking priority. The serving plane derives every compliance guarantee from this metadata, not from the LLM.

---

## 4. Serving Plane — End-to-End Request Data Flow

### 4.1 Master flow (all branches)

```mermaid
flowchart TD
    q[/User query text/]:::ext --> ui[UI captures query]:::proc
    ui -->|POST /api/query JSON| api[FastAPI handler]:::proc
    api --> pii{{PII Guard<br/>regex scan}}:::dec

    pii -->|match found| piiResp[Build PII rejection<br/>no echo, no store]:::proc
    piiResp --> fmt

    pii -->|clean| cls{{Classifier<br/>rules then LLM fallback}}:::dec

    cls -->|ADVISORY| refuse[Refusal responder<br/>+ educational link]:::proc
    cls -->|OUT_OF_SCOPE| scope[Scope responder<br/>+ AMC link]:::proc
    cls -->|FACTUAL| embed[Embed query<br/>all-MiniLM-L6-v2]:::proc

    refuse --> fmt
    scope --> fmt

    embed --> qvec[Query vector]:::proc
    qvec --> search[Vector similarity search<br/>top-k=4..6 + threshold]:::proc
    search <--> idx[(Vector Index)]:::store
    search --> thr{{Any chunk<br/>above threshold?}}:::dec

    thr -->|no| idk[Fallback:<br/>not in my sources]:::proc
    idk --> fmt

    thr -->|yes| filt[Optional metadata filter<br/>by scheme_name / data_type]:::proc
    filt --> ctx[Build grounded context<br/>top chunks + metadata]:::proc
    ctx --> gen[LLM grounded generation<br/>Groq]:::proc
    gen <--> llm[/Groq LLM/]:::ext
    gen --> draft[Draft answer + chosen source_url + scrape_date]:::proc
    draft --> fmt

    fmt[Response Formatter<br/>≤3 sentences · 1 citation ∈ allow-list<br/>footer · PII echo scan]:::proc
    fmt --> resp([Formatted response<br/>answer + link + footer]):::term
    resp --> uiOut[UI renders]:::proc
    uiOut --> shown([Shown to user]):::term

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef store fill:#fff2cc,stroke:#d6a700,color:#5c4500
    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

### 4.2 Sequence diagram — the FACTUAL happy path

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant UI as Frontend
    participant API as FastAPI
    participant PII as PII Guard
    participant CLS as Classifier
    participant EMB as Embedder
    participant VS as Vector Store
    participant LLM as Groq LLM
    participant FMT as Formatter

    U->>UI: types "expense ratio of HDFC Mid Cap?"
    UI->>API: POST /api/query {query}
    API->>PII: scan(query)
    PII-->>API: clean (no PII)
    API->>CLS: classify(query)
    Note over CLS: rule pass matches "expense ratio" → FACTUAL
    CLS-->>API: FACTUAL {scheme_hint, data_type_hint}
    API->>EMB: embed(query)
    EMB-->>API: query_vector (384-dim)
    API->>VS: search(query_vector, k=5, filter)
    VS-->>API: top chunks + metadata + scores
    Note over API: best score ≥ threshold → proceed
    API->>LLM: generate(system_prompt, context_chunks)
    LLM-->>API: draft answer (grounded)
    API->>FMT: format(answer, source_url, scrape_date)
    Note over FMT: ≤3 sentences ✓ · citation ∈ allow-list ✓ · footer ✓ · no PII ✓
    FMT-->>API: final response
    API-->>UI: {answer, source_url, last_updated, response_type}
    UI-->>U: answer + clickable link + "Last updated from sources: June 2026"
```

### 4.3 Sequence diagram — PII rejection (short-circuit)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant UI as Frontend
    participant API as FastAPI
    participant PII as PII Guard
    participant FMT as Formatter

    U->>UI: "my PAN is ABCDE1234F, expense ratio?"
    UI->>API: POST /api/query {query}
    API->>PII: scan(query)
    Note over PII: PAN regex matches → REJECT
    PII-->>API: BLOCKED (do not echo, do not store)
    API->>FMT: format(pii_rejection_message)
    FMT-->>API: standardized rejection + disclaimer
    API-->>UI: {answer: rejection, refused: true}
    UI-->>U: "I cannot process requests containing personal information..."
    Note over U,FMT: Query never reaches classifier, retrieval, or LLM
```

---

## 5. Decision Logic Data Flow

### 5.1 PII Guard — deterministic gate

```mermaid
flowchart TD
    inp[/Clean-input candidate/]:::ext --> pan{{PAN<br/>[A-Z]5[0-9]4[A-Z]?}}:::dec
    pan -->|yes| block
    pan -->|no| aad{{Aadhaar<br/>12 digits?}}:::dec
    aad -->|yes| block
    aad -->|no| ph{{Phone<br/>[6-9] + 9 digits?}}:::dec
    ph -->|yes| block
    ph -->|no| em{{Email<br/>regex?}}:::dec
    em -->|yes| block
    em -->|no| acc{{Account no.<br/>8-18 digits?}}:::dec
    acc -->|yes| block
    acc -->|no| otp{{OTP<br/>4-6 digits in context?}}:::dec
    otp -->|yes| block
    otp -->|no| pass([Pass to Classifier]):::term
    block([REJECT — no echo, no store]):::term

    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

### 5.2 Classifier — hybrid routing (rules first, LLM fallback)

```mermaid
flowchart TD
    cq[/Clean query/]:::ext --> rules{{Rule pass:<br/>advisory keywords?<br/>should I / better / predict / returns will}}:::dec
    rules -->|match| adv([ADVISORY → refusal]):::term
    rules -->|no match| factkw{{Factual data-type<br/>keywords present?<br/>expense ratio / lock-in / SIP ...}}:::dec
    factkw -->|yes| schemechk{{Scheme in<br/>registry/aliases?}}:::dec
    schemechk -->|yes| fact([FACTUAL → retrieval]):::term
    schemechk -->|no, but general MF concept| fact
    schemechk -->|no, unknown scheme| oos([OUT_OF_SCOPE → scope responder]):::term
    factkw -->|ambiguous| llmfb[LLM fallback classifier<br/>returns one label]:::proc
    llmfb --> lbl{{Label?}}:::dec
    lbl -->|FACTUAL| fact
    lbl -->|ADVISORY| adv
    lbl -->|OUT_OF_SCOPE| oos
    lbl -->|borderline-answerable| fact

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

### 5.3 Retrieval scoring & citation selection

```mermaid
flowchart TD
    qv[/Query vector/]:::ext --> knn[Cosine similarity vs all chunks]:::proc
    knn --> topk[Take top-k = 4..6]:::proc
    topk --> gate{{max score ≥<br/>threshold?}}:::dec
    gate -->|no| idk([I don't have this in my sources]):::term
    gate -->|yes| mfilter[Apply metadata filter<br/>scheme_name / data_type hints]:::proc
    mfilter --> rank[Rank by score<br/>tie-break by source_type priority<br/>groww/amc > sebi/amfi for scheme facts]:::proc
    rank --> pick[Select citation =<br/>source_url of top supporting chunk]:::proc
    pick --> ctxout([Context chunks + citation + scrape_date]):::term

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

### 5.4 Response Formatter — final compliance gate

```mermaid
flowchart TD
    draft[/Draft answer + source_url + scrape_date/]:::ext --> s1{{≤ 3 sentences?}}:::dec
    s1 -->|no| trunc[Truncate / regenerate shorter]:::proc
    trunc --> s1
    s1 -->|yes| s2{{Exactly one citation?}}:::dec
    s2 -->|no| fixcite[Force single citation]:::proc
    fixcite --> s2
    s2 -->|yes| s3{{Citation ∈ 20-URL allow-list?}}:::dec
    s3 -->|no| replace[Replace with valid corpus URL<br/>or fall back to I don't know]:::proc
    replace --> s3
    s3 -->|yes| s4[Append footer<br/>Last updated from sources: scrape_date]:::proc
    s4 --> s5{{Any PII in output?}}:::dec
    s5 -->|yes| scrub[Scrub / block]:::proc
    scrub --> s5
    s5 -->|no| out([Compliant response]):::term

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

---

## 6. Request Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Received
    Received --> PIIScan
    PIIScan --> Rejected: PII detected
    PIIScan --> Classifying: clean
    Classifying --> Refusing: ADVISORY
    Classifying --> ScopeBounding: OUT_OF_SCOPE
    Classifying --> Retrieving: FACTUAL
    Retrieving --> NoSource: below threshold
    Retrieving --> Generating: chunks found
    Generating --> Formatting
    Refusing --> Formatting
    ScopeBounding --> Formatting
    NoSource --> Formatting
    Rejected --> Formatting
    Formatting --> Returned: passes all checks
    Formatting --> Generating: regenerate (>3 sentences / bad citation)
    Returned --> [*]
```

Every terminal path converges on **Formatting**, guaranteeing the output contract (≤3 sentences, one corpus citation, freshness footer, no PII) regardless of which branch produced the content.

---

## 7. Data Contracts (API payloads)

### 7.1 Request

```json
POST /api/query
Content-Type: application/json

{ "query": "What is the expense ratio of HDFC Mid Cap Fund?" }
```

### 7.2 Response (unified schema for all branches)

```json
{
  "answer": "The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.74% (Direct Plan). ...",
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "last_updated": "June 2026",
  "response_type": "FACTUAL | ADVISORY_REFUSAL | OUT_OF_SCOPE | NO_SOURCE | PII_REJECTED",
  "refused": false
}
```

| Field | Source of value | Notes |
|-------|-----------------|-------|
| `answer` | Generator or static responder | Always ≤3 sentences |
| `source_url` | Selected chunk metadata, validated vs allow-list | Exactly one; omitted/educational link for refusals |
| `last_updated` | `scrape_date` of cited chunk | Drives the freshness footer |
| `response_type` | Classifier + retrieval outcome | Enables UI styling/telemetry |
| `refused` | Guardrail/classifier | `true` for PII + advisory paths |

### 7.3 Auxiliary endpoints (read-only metadata)

| Endpoint | Returns | Data source |
|----------|---------|-------------|
| `GET /api/health` | service + index status | in-memory check |
| `GET /api/examples` | 3 pre-loaded example questions | static config |
| `GET /api/meta` | scrape date, 6-scheme list | index metadata + scheme registry |

---

## 8. Data Stores & Ownership

```mermaid
flowchart LR
    subgraph Offline
      ing[Ingestion pipeline]:::proc
    end
    subgraph Disk[Local disk — free, no managed DB]
      idx[(Vector Index<br/>Chroma/FAISS)]:::store
      src[(sources.json)]:::store
      reg[(scheme registry + aliases)]:::store
    end
    subgraph Online
      serve[Serving pipeline]:::proc
    end
    ing -->|write/replace| idx
    src -->|read| ing
    src -->|read| serve
    reg -->|read| serve
    idx -->|read-only| serve

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef store fill:#fff2cc,stroke:#d6a700,color:#5c4500
```

| Store | Owner (writer) | Readers | Lifecycle |
|-------|----------------|---------|-----------|
| Vector Index | Ingestion only | Serving (read-only) | Rebuilt on each ingestion run; replaces prior index |
| `sources.json` | Maintainer (manual) | Ingestion + Formatter (allow-list) | Versioned in git; single source of truth |
| Scheme registry | Maintainer (manual) | Classifier + Scope responder | Canonical names + aliases (e.g., "HDFC Equity Fund" ↔ Flexi Cap) |

**No user data is ever persisted.** Single-turn, stateless serving means queries are processed in memory and discarded; PII-flagged inputs are never logged.

---

## 9. Freshness & Re-Ingestion Data Flow

```mermaid
flowchart LR
    trig[/Manual or scheduled trigger/]:::ext --> rerun[Re-run ingestion]:::proc
    rerun --> newdate[Stamp fresh scrape_date]:::proc
    newdate --> rebuild[Rebuild vectors]:::proc
    rebuild --> swap[Replace persisted index]:::proc
    swap --> idx[(Vector Index)]:::store
    idx --> footer[Serving reads new scrape_date]:::proc
    footer --> shown([Footer shows new date in every answer]):::term

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef store fill:#fff2cc,stroke:#d6a700,color:#5c4500
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

Freshness is a pure data property: the footer date is read from the cited chunk's `scrape_date`, so a re-ingestion automatically updates what users see — no code change required.

---

## 10. Error & Fallback Data Paths

```mermaid
flowchart TD
    req[/Request/]:::ext --> try{{Stage outcome}}:::dec
    try -->|LLM timeout/error| e1[Graceful error<br/>suggest retry · never fabricate]:::proc
    try -->|no chunk ≥ threshold| e2[I don't have this in my sources]:::proc
    try -->|ambiguous| e3[Default FACTUAL if answerable<br/>else short clarifying question]:::proc
    try -->|two schemes| e4[Answer both if clear<br/>else clarify]:::proc
    try -->|non-English| e5[Answer in English<br/>or state language limit]:::proc
    try -->|index unavailable| e6[Health fails → 503<br/>UI shows downtime msg]:::proc
    e1 --> fmt[Formatter]:::proc
    e2 --> fmt
    e3 --> fmt
    e4 --> fmt
    e5 --> fmt
    fmt --> out([Compliant response or error]):::term

    classDef proc fill:#e6f0ff,stroke:#3366cc,color:#0a2a66
    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

| Failure | Data behavior | Never does |
|---------|---------------|------------|
| LLM error/timeout | Returns retry message | Fabricate an answer |
| Below-threshold retrieval | Returns "not in sources" | Guess from outside corpus |
| Ambiguous query | Defaults to factual or asks one clarifier | Assume advisory intent silently |
| Index down | 503 + friendly UI message | Serve stale/empty hallucination |

---

## 11. Compliance Checkpoints Along the Data Path

```mermaid
flowchart LR
    A[Query in]:::ext --> C1{{CP1: PII gate<br/>no echo/store}}:::dec
    C1 --> C2{{CP2: advisory refusal<br/>no opinions}}:::dec
    C2 --> C3{{CP3: grounding<br/>context-only}}:::dec
    C3 --> C4{{CP4: citation ∈ allow-list}}:::dec
    C4 --> C5{{CP5: ≤3 sentences + footer}}:::dec
    C5 --> C6{{CP6: PII echo scan}}:::dec
    C6 --> Out([Answer out]):::term

    classDef dec fill:#fde9e9,stroke:#cc3333,color:#7a1f1f
    classDef ext fill:#e8f5e9,stroke:#33aa55,color:#1d5c2e
    classDef term fill:#f0e6ff,stroke:#7a33cc,color:#3d1a66
```

| Checkpoint | Enforces (context constraint) | Where in data flow |
|------------|-------------------------------|--------------------|
| CP1 | No PII collection/storage/echo | Before classify/retrieve/generate |
| CP2 | No advice/opinions/predictions | Classifier branch |
| CP3 | No hallucination | Generation grounded only in retrieved context |
| CP4 | Citations only from 20 URLs | Formatter allow-list validation |
| CP5 | ≤3 sentences + freshness footer | Formatter |
| CP6 | No PII leakage in output | Formatter final scan |

---

## 12. Summary

- **Two clean data planes:** ingestion writes the index; serving reads it. The vector index + `sources.json` + scheme registry are the only persistent data.
- **Metadata is the backbone:** citation, freshness, filtering, and ranking all derive from chunk metadata, not from the model — that is what makes the system traceable and hallucination-resistant.
- **Every path converges on the Formatter**, which is the single enforcement point for the output contract.
- **Six compliance checkpoints** sit directly on the data path, in order, so a violation is structurally hard to reach.
- **Fully free data path:** local embeddings, local vector store, Groq free-tier LLM — no paid service touches any stage.

---

*Companion to `Docs/architecture.md` and `Docs/context.md`. Diagrams are Mermaid; render in any Mermaid-aware Markdown viewer (GitHub, VS Code preview, MkDocs, etc.).*
