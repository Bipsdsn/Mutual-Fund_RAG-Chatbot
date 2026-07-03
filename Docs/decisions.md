# Decisions Log: RAG-Based Mutual Fund FAQ Chatbot

> **Why this file exists:** to record every non-obvious choice and its reasoning, so it is not silently undone later. Two lines per decision: **the choice** and **why**.
> Format: `D-<n> · Decision · Why · (alternatives rejected)`. If you want to reverse a decision, add a new entry that supersedes it — do not delete history.
> Source docs: `context.md`, `architecture.md`, `data-flow-architecture.md`, `implementation-plan.md`, `conventions.md`, `edgecases.md`, `evals.md`, Problem Statement.

> **Status legend:** ✅ active · ⚠️ revisit if constraints change · ⛔ superseded (see linked entry).

---

## 1. Cost & Platform

**D-1 · Entire stack is free, $0/month. ✅**
Why: the build must cost nothing (user constraint); local embeddings + local vector DB + free LLM tier remove every recurring bill. Rejected: any paid API/managed service.

**D-2 · LLM = Groq free tier (Llama 3.x). ✅**
Why: explicitly chosen by the user; fastest free inference with generous limits and an OpenAI-style SDK. Rejected: GPT-4o-mini (paid), Gemini free tier (kept as nothing; user picked Groq), local Ollama (slower on CPU, heavier setup).

**D-3 · Embeddings = local `sentence-transformers/all-MiniLM-L6-v2`. ✅**
Why: free, runs on CPU, no API key, 384-dim is plenty for a 20-page corpus. Rejected: OpenAI `text-embedding-3-small` (paid), larger BGE models (slower; MiniLM is sufficient).

**D-4 · Vector store = ChromaDB (local, persistent). ✅**
Why: free, file-based, zero infra, trivial metadata filtering for a tiny corpus. Rejected: Pinecone (paid/managed), FAISS (kept as fallback; Chroma has nicer metadata + persistence ergonomics).

**D-5 · Hosting = free tier (HF Spaces / Render / Vercel) or local demo video. ✅**
Why: satisfies the "working prototype" deliverable at $0; HF Spaces can bundle everything. Rejected: any paid container/VM.

---

## 2. Architecture Shape

**D-6 · Two decoupled planes: offline ingestion (write) vs online serving (read-only). ✅**
Why: keeps query latency low, makes the index reproducible, and prevents accidental index writes during a request. Rejected: scraping/embedding at query time (slow, fragile, non-deterministic).

**D-7 · Fixed pipeline order: PII → classify → retrieve → generate → format. ✅**
Why: compliance must be enforced before any cost/LLM work; the Formatter must be the last universal gate. Rejected: any reordering (e.g., retrieve-then-classify) — would leak advisory/PII handling.

**D-8 · The Formatter is the single output gate for every branch. ✅**
Why: guarantees the output contract (≤3 sentences, one citation, footer, no PII) regardless of which branch produced text. Rejected: per-branch formatting (drift, missed invariants).

**D-9 · Stateless, single-turn (no conversation memory) in v1. ✅**
Why: strongest privacy posture (nothing to store), simplest to reason about, matches the brief. Rejected: chat memory (adds PII/storage risk, scope creep).

**D-10 · Determinism where possible: regex/rules for PII + format; LLM only for language. ✅**
Why: guardrails must be predictable and testable offline; LLMs are non-deterministic. Rejected: LLM-only PII/format enforcement (unreliable, untestable).

---

## 3. Guardrails & Compliance

**D-11 · PII detection is regex-based and runs first, short-circuiting. ✅**
Why: deterministic, fast, offline-testable; blocking before the LLM also saves quota and prevents any echo. Rejected: ML PII model (overkill, heavier, less predictable).

**D-12 · OTP/account-number detection is context-gated by keywords. ✅**
Why: raw long-digit rules false-positive on AUM/NAV figures in legitimate questions (edge PII-7). Rejected: unconditional digit-length rules (block valid fact queries).

**D-13 · Classifier is hybrid: fast rule pass first, LLM fallback only for ambiguous. ✅**
Why: clear advisory/factual cases are caught cheaply and deterministically; LLM handles the gray zone. Rejected: pure-LLM classifier (slower, costs quota, less predictable) and pure-rules (misses nuance).

**D-14 · Ambiguous queries default to FACTUAL-if-answerable, else clarify. ✅**
Why: the brief says prefer a factual interpretation; avoids over-refusing real questions (edge #4). Rejected: defaulting to refusal (frustrating, fails SC1).

**D-15 · Comparing a stated numeric fact is FACTUAL, not advisory. ✅**
Why: "which has lower expense ratio" is verifiable data, not an opinion; only "better/should I" are advisory (edge ADV-7/ADV-8). Rejected: refusing all comparisons (would fail legitimate factual asks).

**D-16 · Refusals and PII rejections return HTTP 200 with a `response_type`, not 4xx. ✅**
Why: they are valid, expected, compliant responses with a body the UI renders. Rejected: 4xx (misrepresents them as errors; complicates the client).

---

## 4. Retrieval & Generation

**D-17 · Citation and freshness come from chunk metadata, never from the LLM. ✅**
Why: the model can hallucinate URLs/dates; metadata is verifiable and traceable. Rejected: asking the model to "include the source" (unreliable, violates SC3).

**D-18 · Score threshold gates retrieval; below it → "I don't have this in my sources." ✅**
Why: this is the primary anti-hallucination mechanism (SC14, edge RET-2). Rejected: always answering from top-k (invents facts when corpus lacks them).

**D-19 · Grounded-only generation: context = retrieved chunks, no external knowledge. ✅**
Why: "accuracy over intelligence" core principle; prevents the model's training data from leaking in. Rejected: open generation (hallucination risk).

**D-20 · `temperature = 0.0` for generation and classification. ✅**
Why: facts need determinism and repeatable evals, not creativity. Rejected: higher temperature (variance breaks tests and consistency).

**D-21 · Exactly one citation per answer; tie-break by source_type priority (groww/amc > sebi/amfi for scheme facts). ✅**
Why: the brief mandates one link; scheme-specific facts are most authoritative on Groww/AMC pages. Rejected: multiple citations (violates format) or no priority (wrong source chosen).

**D-22 · Metadata pre-filter by `scheme_name`/`data_type` using classifier hints. ✅**
Why: on a 20-page corpus this sharply improves precision and avoids cross-scheme bleed (edge RET-10). Rejected: pure vector search (Mid/Small/Large cap chunks look similar).

**D-23 · Chunking ~500–800 tokens, ~80 overlap, via RecursiveCharacterTextSplitter. ✅**
Why: keeps a full fact (e.g., exit-load structure) intact while preserving boundaries; overlap avoids splitting a value from its label. Rejected: tiny chunks (fragment facts) or whole-page chunks (dilute retrieval).

---

## 5. Ingestion

**D-24 · Per-URL `fetch_mode` (html_static / html_js / pdf) in `sources.json`. ✅**
Why: Groww pages are JS-rendered (need Playwright) while AMFI/SEBI are static; PDFs need a different loader. Rejected: one fetch method for all (empty bodies on JS pages — edge ING-1).

**D-25 · `sources.json` is the single source of truth for the 20-URL allow-list. ✅**
Why: both ingestion and the citation validator read it, so "official sources only" is enforced in one place. Rejected: hardcoding URLs in code (drift, duplication).

**D-26 · Ingestion is idempotent: a re-run replaces the index and re-stamps `scrape_date`. ✅**
Why: freshness becomes a pure data property; no stale duplicates accumulate (edge ING-7). Rejected: incremental appends (dupes, inconsistent dates).

**D-27 · Cache raw HTML/PDF locally during dev (`data/raw_cache/`, git-ignored). ✅**
Why: avoids re-hitting sites while iterating on cleaning/extraction; mitigates anti-bot/rate limits (edge ING-2). Rejected: re-fetching every run (slow, risks blocks).

**D-28 · If a page blocks scraping, fall back to its AMC PDF or document the gap. ✅**
Why: keeps the index buildable and honest rather than failing the whole run (edge ING-8). Rejected: hard-failing on one bad URL.

**D-29 · Same embedding model at ingest and query time (asserted in config). ✅**
Why: vectors from different models are not comparable — mismatch silently destroys retrieval (edge ING-10). Rejected: swapping models without re-ingesting.

---

## 6. Backend & API

**D-30 · FastAPI for the backend. ✅**
Why: async, typed (Pydantic), auto OpenAPI docs, strong RAG ecosystem, free. Rejected: Flask (less typing/async ergonomics), Django (too heavy for this).

**D-31 · Unified response schema `{answer, source_url, last_updated, response_type, refused}` for all branches. ✅**
Why: one contract the UI can always render; `response_type` drives styling/telemetry. Rejected: different shapes per branch (client complexity).

**D-32 · `config.py` is the only module that reads `os.environ`; fail-fast on missing key. ✅**
Why: centralizes config, prevents scattered env reads, and surfaces misconfig at startup not mid-request (edge SYS-3). Rejected: ad-hoc `os.getenv` calls everywhere.

**D-33 · Single Groq call wrapper with timeout + limited retries/backoff. ✅**
Why: one choke point for reliability, logging (latency only), and free-tier rate-limit handling (edge SYS-2). Rejected: scattered direct SDK calls.

**D-34 · Logs record `response_type`/label/score/latency only — never raw PII inputs. ✅**
Why: privacy constraint; logging a flagged query would itself store PII (edge PII-10). Rejected: verbose request logging.

**D-35 · Auth is omitted in the prototype, but `/api/query` is flagged for rate-limiting before public deploy. ✅⚠️**
Why: speeds the prototype; an open LLM endpoint can be abused for cost/injection, so a public live link needs throttling. Rejected: shipping a public unauthenticated endpoint without noting the risk.

---

## 7. Frontend

**D-36 · UI = React (Vite), built to a HIGH quality bar (not minimal). ✅**
Why: the user explicitly wants a very high-quality frontend; React delivers the polished "full product" deliverable with a real design system, responsive layout, accessibility, and per-response-type styling. Streamlit remains only an emergency time-crunch fallback. Implemented in Phase 9 (do not build before its prerequisites).

**D-37 · Single-turn UI holds only the current query + latest response. ✅**
Why: matches the stateless backend and privacy posture; nothing persisted client-side either. Rejected: chat history (scope creep, privacy surface).

**D-38 · Disclaimer is always visible, not a dismissible banner. ✅**
Why: "Facts-only. No investment advice." is a hard requirement (SC8) and a compliance signal. Rejected: one-time/dismissible notice.

---

## 8. Testing & Process

**D-39 · Guardrail/formatter tests run offline with Groq mocked. ✅**
Why: they must be deterministic, fast, and CI-friendly; compliance can't depend on a live LLM. Rejected: live-LLM tests for guardrails (flaky, slow, costs quota).

**D-40 · Evals are written before each phase and gate progression. ✅**
Why: defines "done" objectively and prevents shipping un-verified phases (`evals.md`). Rejected: testing after the fact (scope drift, missed criteria).

**D-41 · Build the thin end-to-end slice (P4) before hardening layers. ✅**
Why: de-risks the riskiest integration (Groq + embedding match + Chroma read) early. Rejected: building each layer fully before any integration (late surprises).

**D-42 · `edgecases.md` is a living doc; discovered cases get logged and promoted to tests. ✅**
Why: captures real-world messiness and converts it into regressions. Rejected: relying on memory/ad-hoc fixes.

**D-43 · The AI never runs `git push`/`git commit`; the user owns git history. ✅**
Why: explicit submission rule — the user pushes and submits the GitHub link. Rejected: AI-driven git operations.

**D-44 · `requirements.txt` versions are pinned. ✅**
Why: reproducible installs across machines/hosts (DoD). Rejected: unpinned ranges (drift, "works on my machine").

---

## 9. Scope Boundaries (deliberate non-goals)

**D-45 · Direct Growth plans only; Regular/IDCW are out of scope. ✅**
Why: the corpus contains Direct-plan pages; answering Regular would require ungrounded data (edge SCO-3). Rejected: guessing Regular-plan figures.

**D-46 · English-only in v1; non-English → answer in English or state the limitation. ✅**
Why: corpus and prompts are English; multilingual handling is scope creep for the deadline (edge LNG-1). Rejected: silent partial multilingual support.

**D-47 · Corpus fixed at 20 official URLs; no third-party sources ever. ✅**
Why: hard constraint (no Moneycontrol/ET Money/etc.); guarantees citation trustworthiness. Rejected: augmenting with blogs for coverage.

**D-48 · No returns/performance computation; route to the official factsheet link. ✅**
Why: explicit content restriction (no calculations/predictions). Rejected: computing or estimating returns.

---

## 10. Open / Revisit Later (⚠️)

**D-49 · Score threshold tuned to 0.65 against the built index (bge-small local backend). ✅**
Why: on the real 2,575-chunk index, legitimate queries score ~0.71–0.84 while off-topic queries ("who won the 2018 World Cup", "capital of France") score ~0.50–0.57 — the SID legal text made the old 0.35 far too permissive (off-topic matched → hallucination risk, SC14). 0.65 cleanly separates them; updated `config.py` default + `.env`. Revisit for the production all-MiniLM backend (different score distribution).

**D-50 · Two-scheme / multi-fact queries may pick a primary citation or ask to split. ⚠️**
Why: the one-citation + ≤3-sentence contract limits how much can be answered at once (edge RET-3/RET-4). Revisit if the format rules are relaxed.

**D-51 · Groq model pinned to a specific Llama 3.x id via `GROQ_MODEL`. ⚠️**
Why: keeps behavior stable; free-tier model availability can change. Revisit if Groq deprecates the chosen model.

**D-52 · Local verification backend: numpy vector store + fastembed embeddings (compiler-free). ✅⚠️**
Why: ChromaDB's native `hnswlib` has no Python-3.13 wheel and needs a C++ compiler, which blocks the committed Chroma path on this machine; `sentence-transformers` also pulls heavy PyTorch. To verify the live retrieve→generate→/api/query round trip in-session at $0, added `backend/rag/local_store.py` (numpy cosine store mimicking Chroma's `query()` API so the retriever is unchanged) and `backend/rag/local_embed.py` (fastembed BAAI/bge-small-en-v1.5, same model both sides — D-29 preserved). Production default remains ChromaDB + sentence-transformers (D-3, D-4), which works on Python ≤3.12. Revisit: consider making the backend a first-class config toggle, or pin the project to Python 3.11/3.12.

---

## 11. Phase 6 — Query Classifier (added 2026-06-25)

**D-53 · Classifier is a deterministic rule pass with a Groq fallback only for ambiguous queries. ✅**

Why: zero advisory leakage is mandatory (SC4/E-6.1) and must not depend on a flaky/paid LLM call; rules decide the gate cases offline while the LLM only breaks genuine ties. Rejected: LLM-first classification (non-deterministic, costs quota, can leak advice).

**D-54 · Advisory gate runs FIRST, before scope/factual checks. ✅**

Why: an opinion question that also names a covered scheme ("Is HDFC Mid Cap a good fund?") must refuse, not answer; checking advisory first guarantees no advisory leaks through the factual branch (ADV-8). Rejected: scheme/factual detection first (would answer disguised opinions).

**D-55 · Judgment adjectives (good/best/better/worth) are treated as advisory. ✅**

Why: they request an opinion, not a fact; this catches disguised advice (E-6.6) and prompt injection ("recommend a fund", E-6.7). Trade-off accepted: a rare factual phrasing using "better" is refused rather than risk leakage. Note "lower/higher expense ratio" comparisons stay FACTUAL (E-6.8) because they compare stated facts, not opinions.

**D-56 · Out-of-scope = competitor-AMC list + uncovered-scheme keyword list, gated on no covered-scheme match. ✅**

Why: "SBI Small Cap" contains the covered alias "small cap", so a competitor-brand check must override alias resolution (E-6.4); uncovered HDFC schemes ("Balanced Advantage", E-6.3) are caught by keyword only when no covered scheme resolves, so benchmark questions mentioning "Nifty" for a covered fund aren't misrouted. Rejected: relying on alias resolution alone (would misclassify competitors/uncovered schemes as in-scope).

**D-57 · General MF-concept questions ("what is an expense ratio?") route FACTUAL even with no scheme named. ✅**

Why: these are answerable from the AMFI/SEBI corpus pages (SCO-6/E-6.9); only a *named* uncovered scheme or competitor is out of scope. Rejected: treating scheme-less questions as out-of-scope (would refuse legitimate educational queries).

**D-58 · `data_type_hint` is granular (e.g. `expense_ratio`); only `scheme_hint` is passed to the retriever's metadata filter. ✅**

Why: granular hints satisfy telemetry/eval E-6.10, but chunk metadata `data_type` is coarse (`scheme_facts` etc.), so filtering on a granular value would always miss and fall back; `scheme_name` filtering is reliable and meaningful. Revisit if ingestion starts tagging granular `data_type` per chunk.

**D-59 · Phase-6 advisory/scope branch messages live inline in `main.py` as minimal placeholders. ✅⚠️**

Why: the dedicated refusal/scope responders + strict Formatter (footer, single-citation enforcement) are Phase 7; Phase 6 only needs correct routing + a compliant-enough response with an allow-listed link. Revisit in P7: replace with `backend/responders/refusal.py` and `scope.py`.

---

## 12. Phase 7 — Generation Contract + Formatter (added 2026-06-25)

**D-60 · The Formatter is the single output gate; every branch returns through it. ✅** (supersedes D-59's inline messages)

Why: ≤3 sentences + one corpus citation + footer + no-PII must hold on factual, refusal, scope, no-source, AND PII branches; centralizing enforcement in `backend/formatter.py` guarantees no branch can skip the contract (conventions §6, INV-1..4). Rejected: per-branch formatting in `main.py` (easy to drift, already caused placeholder duplication).

**D-61 · Sentence splitting breaks only on `.?!` followed by whitespace. ✅**

Why: decimals ("0.74%", NAV "1234.56") and URLs ("investor.sebi.gov.in/riskometer.html") contain dots NOT followed by a space, so this rule never miscounts them as sentence ends (the Phase-7 gotcha). Rejected: naive `split('.')` (would over-count and wrongly trim valid answers).

**D-62 · The disclaimer ("Facts-only. No investment advice.") is the universal footer; the freshness line is added only for factual answers. ✅**

Why: refusal/scope/no-source/PII have no `scrape_date`, but every branch still needs a footer (E-7.3); the freshness line "Last updated from sources: <date>" only makes sense when a cited chunk exists (E-7.4). `compose()` is idempotent so the disclaimer is never duplicated.

**D-63 · On any contract violation the Formatter degrades to NO_SOURCE rather than ship a risky answer. ✅**

Why: an empty draft, an out-of-corpus citation, or PII leaking into the draft are all safer to answer with "I don't have this in my sources" than to emit something ungrounded or privacy-violating (FMT-3/6/10, PII-10, SC14). Rejected: best-effort repair that could still ship a bad citation or leaked PII.

**D-64 · Citation/link URLs live in `corpus.py` (`EDUCATIONAL_URL`, `AMC_HOME_URL`) as the single source of truth. ✅**

Why: the classifier and both responders need the same AMFI/AMC links; defining them once in `corpus` (and aliasing in `classifier`) prevents drift and keeps them inside the allow-list. Rejected: duplicating literal URLs across modules.

---

## 13. Hybrid Retrieval — structured-first + semantic fallback (added 2026-06-25)

**D-65 · Scheme facts are answered from an exact (scheme × data_type) table before any embedding search. ✅**

Why: for a facts-only bot over 6 known schemes + a fixed set of fact types, a keyed lookup returns the verbatim scraped value with its own citation — it cannot mismatch to a similar-but-wrong chunk (edge RET-10) the way pure vector similarity can. The classifier's `scheme_hint` + `data_type_hint` (D-58) are the lookup key; embedding search is the fallback for educational/open questions. Rejected: pure semantic RAG for scheme facts (probabilistic, can retrieve the wrong scheme's number).

**D-66 · The fact store has two layers: seeded regulatory facts (code) + scraped facts (`data/facts.json`); seeded wins. ✅**

Why: lock-in and the ELSS Section-80C benefit are fixed by SEBI / the Income Tax Act, so they are derived in code from `schemes.json` (single source of truth) and must not be overwritten by a noisy scrape; volatile market values (expense ratio, NAV, AUM) are written by ingestion. This keeps regulatory answers 100% correct today while numeric facts wait for a real ingest. Rejected: hardcoding numeric market values (staleness / fabrication risk).

**D-67 · Structured facts are rendered deterministically (no LLM) and only cite allow-listed URLs. ✅**

Why: since the value is exact, a template sentence removes any chance of the LLM altering the number, and it saves a Groq call ($0 goal); scraped facts with a citation outside the 20-URL allow-list are dropped at load (INV-6). The Formatter still enforces ≤3 sentences + footer on the rendered sentence. Revisit: allow an optional LLM phrasing pass if answers feel terse.

---

## 14. Phase 8 — API Hardening (added 2026-06-25)

**D-68 · Index-load failure returns HTTP 503 with a friendly detail; Groq failure returns HTTP 200 with a retry message. ✅**

Why: a missing/corrupt index is a real outage (can't serve anything) so 503 is correct (E-8.2); a transient Groq timeout is not an outage and must never fabricate, so we return a safe "try again" message (ResponseType.ERROR) rather than a guess (E-8.6, SYS-1/4). Rejected: 500 + stack trace (leaks internals), or fabricating on LLM failure.

**D-69 · Structured fact answers survive an index outage. ✅**

Why: the fact lookup runs before the semantic retriever, so lock-in / ELSS tax questions still answer correctly even when Chroma is down — the 503 path only guards the embedding fallback. This is a direct benefit of the hybrid design (D-65).

**D-70 · Per-IP rate limiting is deferred to the deploy step, not built into the app now. ✅⚠️**

Why: `/api/query` is unauthenticated; rate limiting matters only for a public link and is best applied at the host/proxy layer to protect the Groq quota (plan §8 security flag). Adding it in-process now would add flaky state and complexity for no local benefit. Revisit at Phase 12 if a public link is chosen.

---

## 15. In-app Re-ingestion Scheduler (added 2026-06-25)

**D-71 · Optional in-app APScheduler for periodic re-ingestion, OFF by default. ✅⚠️** (chosen by user over the GitHub Actions cron I recommended)

Why: gives automatic data refresh without external CI. Kept opt-in via `SCHEDULER_ENABLED` because free hosts sleep when idle (a timer there is unreliable) and frequent scraping risks anti-bot blocks (we already saw hdfcfund 403s). Only makes sense on an always-on deployment. Trade-off vs the recommended GitHub Actions cron (D-note): the in-app timer needs a live server and consumes its resources, whereas CI cron is serverless — but the user prefers self-contained refresh.

**D-72 · The scheduler and ingestion pipeline are lazy-imported and the job never raises. ✅**

Why: importing the app must not drag in the heavy scrape/ML stack or require APScheduler to be installed; and a failed scrape must be logged + swallowed so it never crashes the API (`coalesce=True`, `max_instances=1` also prevent overlapping runs). Rejected: importing ingestion at module load (heavy) or letting job exceptions bubble (would kill the worker).

---

## 16. Phase 9 — Frontend (added 2026-06-25)

**D-73 · React + Vite with a hand-built CSS design system; no UI framework. ✅**

Why: meets the high-quality bar (coherent tokens, responsive, micro-interactions, full a11y) while staying $0 and dependency-light — the only deps are react/react-dom/vite. Rejected: heavy UI kits (MUI/Chakra) — larger bundle, less control over the HDFC/Groww look; Streamlit — faster but not the "very high quality" product the user asked for. Note: Node isn't installed on the dev machine, so `npm install && npm run build` must be run where Node is available (code is complete and self-consistent).

**D-74 · The UI strips the backend's footer lines and re-renders them as structured chrome. ✅**

Why: the API answer text already ends with the freshness line + disclaimer (Formatter contract). The UI removes those and shows the disclaimer once (header + footer) and the freshness/citation as styled elements (source pill + "Updated <date>"), avoiding duplication while keeping the exact same information. The raw contract is unchanged for API consumers.

**D-75 · Vite dev proxy `/api → :8000`; UI uses same-origin relative URLs. ✅**

Why: one code path for dev and prod (no hardcoded host); split deploys override via `VITE_API_BASE` + backend `ALLOWED_ORIGINS`. Rejected: hardcoding `localhost:8000` (breaks in production).

**D-76 · Chat history + account panel on every screen; history persists in `localStorage`. ✅**

Why: user asked for history + account visible on all screens. With no auth backend (out of scope for a facts-only single-turn bot), history is stored client-side per browser and the account is a display-only "Guest / Local session" profile. Real multi-device accounts/sync would need a backend + auth — deliberately not added. The bot itself stays stateless server-side (no user data persisted; privacy invariant intact).

**D-77 · Dark mode with an animated starry-sky background; toggle persists and respects OS preference. ✅**

Why: user requested dark mode + starry animation on every screen. Implemented as pure CSS (parallax twinkling star layers + shooting stars) rendered only in dark mode, behind translucent surfaces; honors `prefers-reduced-motion` for accessibility. Rejected: a canvas/WebGL starfield (heavier, needless for a decorative background).

**D-80 · hdfcfund.com pages are ingested via a manual browser-saved cache, not automated scraping. ✅⚠️**

Why: hdfcfund.com's Akamai WAF hard-blocks automated fetches (plain requests, realistic-UA requests, headless + stealth Chromium all get "Access Denied" — D-9). Rather than escalate WAF evasion (futile here + ToS gray area), the ingest reads a manually-saved copy from `data/raw_cache/<id>.html` when present. Legitimate (human browser access), $0, and keeps the 8 URLs in the citation allow-list. Their content stays absent until cached; scheme facts are unaffected (Groww + seeded). Revisit: supply direct CDN PDF links for factsheet/KIM/SID (pdf mode may not be WAF-walled).

**D-79 · The serving retriever transparently falls back to the local numpy index + fastembed when Chroma/sentence-transformers are unavailable. ✅**

Why: lets the full app serve end-to-end at $0 on Python 3.13 (where the production ML stack won't install — D-52). `_get_collection` tries Chroma first, then loads `data/local_index`; `_default_embed` matches the active backend so query and index vectors stay in the same space (D-29). Production on Python ≤3.12 still uses Chroma + sentence-transformers unchanged. Verified: `/api/health` reports the local index (285 chunks) and fact/retrieval answers are correct.

**D-78 · Frontend visuals aligned to the Stitch "Fiduciary Confidence" design, but real data overrides the mockup's content. ✅**

Why: adopted Stitch's strong cues (centered welcome + icon, full-width example rows with arrow, pill composer with leading search + circular teal send, assistant avatar + footer band, tone-colored left borders) since they match our palette and raise polish. But the Stitch screens hallucinated scheme names (HDFC Top 100 / Mid-Cap Opportunities / Liquid Fund / Balanced Advantage — even using "Balanced Advantage" as both a covered scheme and the out-of-scope example) and wrong example questions. Our UI keeps the **real** six schemes + examples from `/api/meta` and `/api/examples`, so the app is intentionally more correct than the mockup. Icons are inline SVGs (no Material Symbols CDN) to stay offline/$0.

---

*Living log. Add an entry for every non-obvious choice. To change a decision, append a superseding entry (mark the old one ⛔ and link it) rather than editing in place — this is what stops earlier reasoning from being quietly reversed.*
