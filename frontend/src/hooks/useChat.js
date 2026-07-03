import { useCallback, useEffect, useRef, useState } from "react";
import { fetchExamples, fetchMeta, postQuery, ApiError } from "../api.js";
import { FALLBACK_EXAMPLES } from "../constants.js";

const STORE_KEY = "mf.sessions.v1";
const CUR_KEY = "mf.currentId.v1";

let seq = 0;
const uid = (p) => `${p}${Date.now().toString(36)}${(++seq).toString(36)}`;

function loadSessions() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function titleFrom(text) {
  const t = (text || "").trim().replace(/\s+/g, " ");
  return t.length > 42 ? `${t.slice(0, 42)}…` : t || "New chat";
}

function makeSession() {
  return { id: uid("s"), title: "New chat", messages: [], createdAt: Date.now() };
}

// Conversation state with persistent, multi-session history (localStorage) plus
// meta/examples loading. Exposes session management for the sidebar.
export function useChat() {
  const [sessions, setSessions] = useState(() => {
    const loaded = loadSessions();
    return loaded.length ? loaded : [makeSession()];
  });
  const [currentId, setCurrentId] = useState(() => {
    try {
      return localStorage.getItem(CUR_KEY) || null;
    } catch {
      return null;
    }
  });
  const [meta, setMeta] = useState(null);
  const [examples, setExamples] = useState(FALLBACK_EXAMPLES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const lastQueryRef = useRef("");

  // Ensure a valid current session id.
  useEffect(() => {
    if (!currentId || !sessions.some((s) => s.id === currentId)) {
      setCurrentId(sessions[0]?.id ?? null);
    }
  }, [sessions, currentId]);

  // Persist sessions + current id.
  useEffect(() => {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(sessions));
    } catch {}
  }, [sessions]);
  useEffect(() => {
    try {
      if (currentId) localStorage.setItem(CUR_KEY, currentId);
    } catch {}
  }, [currentId]);

  // Load meta + examples once.
  useEffect(() => {
    let alive = true;
    fetchMeta().then((m) => alive && setMeta(m)).catch(() => {});
    fetchExamples()
      .then((e) => alive && e?.examples?.length && setExamples(e.examples))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const current = sessions.find((s) => s.id === currentId) || sessions[0];
  const messages = current?.messages ?? [];

  const _appendToCurrent = useCallback(
    (msg, patch) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === (currentId ?? prev[0]?.id)
            ? { ...s, messages: [...s.messages, msg], ...(patch || {}) }
            : s
        )
      );
    },
    [currentId]
  );

  const send = useCallback(
    async (text) => {
      const query = (text || "").trim();
      if (!query || loading) return;

      lastQueryRef.current = query;
      setError(null);
      setLoading(true);

      const isFirst = messages.length === 0;
      _appendToCurrent(
        { id: uid("m"), role: "user", text: query },
        isFirst ? { title: titleFrom(query) } : null
      );

      try {
        const res = await postQuery(query);
        _appendToCurrent({
          id: uid("m"),
          role: "assistant",
          text: res.answer,
          sourceUrl: res.source_url,
          lastUpdated: res.last_updated,
          responseType: res.response_type,
          refused: res.refused,
        });
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : "Couldn't reach the assistant. Check your connection and try again."
        );
      } finally {
        setLoading(false);
      }
    },
    [loading, messages.length, _appendToCurrent]
  );

  const retry = useCallback(() => {
    if (lastQueryRef.current) send(lastQueryRef.current);
  }, [send]);

  const newChat = useCallback(() => {
    setError(null);
    // Reuse the current session if it's already blank (avoid stacking empties).
    const cur = sessions.find((s) => s.id === currentId);
    if (cur && cur.messages.length === 0) return;
    const s = makeSession();
    setSessions((prev) => [s, ...prev]);
    setCurrentId(s.id);
  }, [sessions, currentId]);

  const selectSession = useCallback((id) => {
    setCurrentId(id);
    setError(null);
  }, []);

  const deleteSession = useCallback(
    (id) => {
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        return next.length ? next : [makeSession()];
      });
    },
    []
  );

  return {
    sessions,
    currentId: current?.id ?? null,
    messages,
    meta,
    examples,
    loading,
    error,
    send,
    retry,
    newChat,
    selectSession,
    deleteSession,
  };
}
