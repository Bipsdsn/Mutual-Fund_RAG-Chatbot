# Deployment Guide — Railway (backend) + Vercel (frontend)

Deploys the **facts-only MF FAQ assistant** on a **$0** split stack:

- **Backend (FastAPI)** → **Railway** — serves `/api/*`, calls Groq.
- **Frontend (React/Vite)** → **Vercel** — static SPA that calls the Railway API.

> **GitHub push is done by you, not the AI.** Push the repo first, then connect
> both platforms to it.

---

## 0. Design choice: ship the compiler-free serving stack

At serve time the app does **not** need the heavy ingestion/production stack
(ChromaDB, sentence-transformers, torch, Playwright, LangChain). The retriever
transparently falls back to the committed **numpy index + fastembed** (decisions
D-52 / D-79). So we deploy with the slim [`requirements-serve.txt`](../requirements-serve.txt),
which keeps the Railway build small, fast, and within the free tier.

**This means the prebuilt index must be committed to git:**

```
data/local_index/embeddings.npy
data/local_index/records.json
data/facts.json
data/sources.json
data/schemes.json
```

Confirm they are tracked (they are not git-ignored):

```bash
git add data/local_index data/facts.json data/sources.json data/schemes.json
git status
```

If you ever rebuild the index locally (`python -m ingestion.run_ingest_local`),
commit the updated files so production picks up fresh data.

---

## 1. Push to GitHub (you)

```bash
git add .
git commit -m "Deploy: MF FAQ assistant (Railway + Vercel)"
git push -u origin main
```

`.env` is git-ignored — **never commit secrets**. The Groq key goes into the
Railway dashboard (Step 2).

---

## 2. Backend on Railway

1. **New Project → Deploy from GitHub repo** → pick this repo.
2. Railway auto-detects Python and uses the repo-root [`Procfile`](../Procfile):
   ```
   web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```
3. **Install command / requirements:** point Railway at the slim file. In
   **Settings → Build**, set the install command to:
   ```
   pip install -r requirements-serve.txt
   ```
   (If Railway insists on `requirements.txt`, either rename `requirements-serve.txt`
   → `requirements.txt` for the deploy, or add a `nixpacks.toml` install phase.)
4. **Variables** (Settings → Variables):
   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | your Groq key (secret) |
   | `GROQ_MODEL` | `llama-3.1-8b-instant` |
   | `SCORE_THRESHOLD` | `0.65` |
   | `MAX_SENTENCES` | `3` |
   | `REQUIRE_SECRETS` | `1` |
   | `SCHEDULER_ENABLED` | `0` |
   | `ALLOWED_ORIGINS` | `https://<your-vercel-app>.vercel.app` |
   | `NIXPACKS_PYTHON_VERSION` | `3.12` |
   | `LOG_LEVEL` | `INFO` |

   > `ALLOWED_ORIGINS` must be the exact Vercel URL (you'll get it in Step 3 — set
   > a placeholder now and update it after the frontend deploys). Comma-separate
   > multiple origins.
5. **Deploy.** Railway builds, installs, and starts uvicorn on `$PORT`.
6. **Health check:** set the healthcheck path to `/api/health` (Settings → Deploy).
   It returns `{"status":"ok","index_loaded":true,"chunk_count":2575,...}` once the
   committed index loads.
7. Copy the public URL, e.g. `https://mf-faq-backend.up.railway.app`.

**Smoke-test the backend:**

```bash
curl https://<railway-url>/api/health
curl -X POST https://<railway-url>/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the lock-in period of HDFC ELSS Tax Saver?"}'
```

Notes:
- First query triggers a one-time fastembed model download (~67 MB) → slight cold-start.
- Free tier sleeps when idle; keep `SCHEDULER_ENABLED=0` (an in-app timer is
  unreliable on sleeping instances — see D-71).

---

## 3. Frontend on Vercel

1. **Add New → Project** → import the same GitHub repo.
2. **Root Directory:** `frontend`. Vercel reads [`frontend/vercel.json`](../frontend/vercel.json)
   (framework `vite`, build `npm run build`, output `dist`, SPA rewrite).
3. **Environment Variable:**
   | Key | Value |
   |---|---|
   | `VITE_API_BASE` | `https://<railway-url>` |

   The frontend calls same-origin `/api/*` by default; `VITE_API_BASE` points it at
   the Railway backend for this split deploy (see `frontend/src/api.js`).
4. **Deploy.** Copy the resulting URL, e.g. `https://mf-faq.vercel.app`.

---

## 4. Wire CORS (connect the two)

Back in **Railway → Variables**, set `ALLOWED_ORIGINS` to the exact Vercel URL:

```
ALLOWED_ORIGINS=https://mf-faq.vercel.app
```

Redeploy the backend (Railway redeploys on variable change). The backend's
CORS middleware only allows this origin — open the Vercel site and ask a question.

---

## 5. Post-deploy verification checklist

Run these on the live site (mirrors the E-10 gate):

- [ ] Factual: "expense ratio of HDFC Mid Cap Fund" → value + Groww citation + footer.
- [ ] Regulatory: "lock-in of HDFC ELSS Tax Saver" → "3 years".
- [ ] Educational: "what is a mutual fund?" → grounded, AMFI/SEBI citation.
- [ ] Advisory: "should I invest in HDFC Mid Cap?" → refused + educational link.
- [ ] Out-of-scope: "SBI Small Cap expense ratio" → scope response.
- [ ] PII: "my PAN is ABCDE1234F …" → rejected, value not echoed.
- [ ] Unknown: "portfolio churn ratio of HDFC Mid Cap" → "I don't have this in my sources."
- [ ] `GET /api/health` returns `status: ok`, `index_loaded: true`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| CORS error in browser console | `ALLOWED_ORIGINS` must exactly match the Vercel URL (scheme + host, no trailing slash); redeploy backend. |
| `503` on `/api/query` | Index didn't load — ensure `data/local_index/*` + `data/facts.json` were committed and deployed. |
| Config error on boot (`GROQ_API_KEY`) | Set `GROQ_API_KEY` in Railway Variables. |
| Frontend calls `localhost` | `VITE_API_BASE` not set at build time — set it in Vercel and redeploy. |
| Slow first response | One-time fastembed model download + free-tier cold start; subsequent queries are fast. |
| Groq `429` | Free-tier rate limit; the SDK retries automatically. Keep prompts short. |

---

## Alternative: all-in-one (optional)

If you prefer a single deploy, Hugging Face Spaces (Docker) can bundle the FastAPI
backend + a Streamlit/served frontend. The split Railway + Vercel setup above is the
recommended $0 path for the React frontend.

## Security reminder

- `/api/query` is unauthenticated. For a public link, consider adding a per-IP rate
  limit at the platform edge (or an API key) to protect the Groq quota (see D-70).
- Rotate the Groq key if it was ever shared in plaintext.
