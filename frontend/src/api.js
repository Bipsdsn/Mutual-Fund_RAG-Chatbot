// Thin API client for the FastAPI backend. Uses relative /api URLs (proxied in
// dev via vite.config.js; same-origin in production). Override with
// VITE_API_BASE for split deployments.
const BASE = import.meta.env.VITE_API_BASE || "";

async function getJSON(path) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new ApiError(`Request failed (${res.status})`, res.status);
  return res.json();
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function fetchMeta() {
  return getJSON("/api/meta");
}

export async function fetchExamples() {
  return getJSON("/api/examples");
}

export async function fetchHealth() {
  return getJSON("/api/health");
}

// POST a query. Returns the unified response contract:
// { answer, source_url, last_updated, response_type, refused }
export async function postQuery(query) {
  const res = await fetch(`${BASE}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ query }),
  });

  if (res.status === 503) {
    throw new ApiError(
      "The service is temporarily unavailable. Please try again shortly.",
      503
    );
  }
  if (res.status === 422) {
    throw new ApiError("Please enter a valid question.", 422);
  }
  if (!res.ok) {
    throw new ApiError(`Something went wrong (${res.status}).`, res.status);
  }
  return res.json();
}
