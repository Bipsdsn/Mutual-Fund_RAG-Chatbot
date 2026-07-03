# Frontend — HDFC MF FAQ Assistant (React + Vite)

A polished, accessible, facts-only chat UI for the FastAPI backend. No paid
services, no UI framework dependencies — just React + Vite + a hand-built CSS
design system.

## Prerequisites

- Node.js 18+ and npm (not required for the Python backend; only to build/run
  this UI).

## Setup

```bash
cd frontend
npm install
```

## Run in development

Start the backend first (from the repo root):

```bash
uvicorn backend.main:app --reload   # serves http://localhost:8000
```

Then the frontend:

```bash
cd frontend
npm run dev                         # serves http://localhost:5173
```

`vite.config.js` proxies `/api/*` to `http://localhost:8000`, so the UI calls
same-origin relative URLs. Point elsewhere with `VITE_API_TARGET`.

## Build for production

```bash
npm run build      # outputs static assets to frontend/dist
npm run preview    # preview the production build locally
```

For a split deploy (UI and API on different origins), set `VITE_API_BASE` to the
API origin at build time, and add that UI origin to the backend's
`ALLOWED_ORIGINS`.

## What it implements (FR 6.5 + quality bar)

- **Persistent sidebar on every screen**: chat **history** (saved conversations
  in `localStorage`, New chat, select, delete) + an **account** block.
- **Dark mode** with an animated **starry-sky** background (parallax twinkling
  star layers + shooting stars); light/dark toggle persists and respects the OS
  preference on first visit. Honors `prefers-reduced-motion`.
- Welcome/empty state with scope (6 covered schemes from `/api/meta`).
- 3 clickable example questions (from `/api/examples`, with a static fallback).
- Always-visible `Facts-only. No investment advice.` disclaimer.
- Question input (Enter to send, Shift+Enter for newline) + send button.
- Answer bubbles with a clickable source link and an `Updated <date>` chip.
- Distinct styling per response type: factual / refusal / out-of-scope /
  no-source / privacy / service-error (colored accent + labelled pill).
- Loading (typing indicator), empty, and error (with Retry) states.
- Accessibility: semantic landmarks, skip link, `aria-live` transcript, labels,
  visible focus rings, keyboard-friendly, responsive drawer sidebar on mobile.

## Notes

- **Account is a local, display-only profile** ("Guest / Local session"). There
  is no auth backend, so it does not log in or sync — history lives only in this
  browser's `localStorage`. Real accounts would need a backend (out of scope).

## Structure

```
src/
  api.js                 # fetch client for /api/query|meta|examples|health
  constants.js           # response-type presentation map + disclaimer
  hooks/useChat.js       # multi-session conversation state + history persistence
  hooks/useTheme.js      # light/dark theme (localStorage + OS preference)
  components/            # Header, Sidebar, StarField, ThemeToggle, Welcome,
                         # MessageList, Message, Composer, ResponseBadge, …
  styles.css             # design tokens (light + dark) + starfield + all styling
```
