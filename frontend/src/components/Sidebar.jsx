import ThemeToggle from "./ThemeToggle.jsx";

function relTime(ts) {
  const s = Math.max(1, Math.floor((Date.now() - ts) / 1000));
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

// Persistent left panel shown on every screen: brand, New chat, the saved chat
// history list, and an account block with the theme switch.
export default function Sidebar({
  sessions,
  currentId,
  onSelect,
  onNew,
  onDelete,
  isDark,
  onToggleTheme,
  open,
  onClose,
}) {
  return (
    <>
      <div
        className={`sidebar__scrim ${open ? "is-open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`sidebar ${open ? "is-open" : ""}`}
        aria-label="Chat history and account"
      >
        <div className="sidebar__top">
          <div className="sidebar__brand">
            <span className="sidebar__mark" aria-hidden="true">MF</span>
            <span className="sidebar__brandtext">FAQ Assistant</span>
          </div>
          <button type="button" className="btn-new" onClick={onNew}>
            <span aria-hidden="true">＋</span> New chat
          </button>
        </div>

        <nav className="sidebar__history" aria-label="Chat history">
          <p className="sidebar__label">History</p>
          {sessions.length === 0 && (
            <p className="sidebar__empty">No conversations yet.</p>
          )}
          <ul className="history-list">
            {sessions.map((s) => (
              <li key={s.id}>
                <div
                  className={`history-item ${s.id === currentId ? "is-active" : ""}`}
                >
                  <button
                    type="button"
                    className="history-item__main"
                    onClick={() => onSelect(s.id)}
                    aria-current={s.id === currentId ? "true" : undefined}
                  >
                    <span className="history-item__title">{s.title}</span>
                    <span className="history-item__time">{relTime(s.createdAt)}</span>
                  </button>
                  <button
                    type="button"
                    className="history-item__del"
                    onClick={() => onDelete(s.id)}
                    aria-label={`Delete conversation: ${s.title}`}
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar__account">
          <div className="account">
            <span className="account__avatar" aria-hidden="true">GU</span>
            <div className="account__info">
              <span className="account__name">Guest</span>
              <span className="account__sub">Local session</span>
            </div>
          </div>
          <ThemeToggle isDark={isDark} onToggle={onToggleTheme} />
        </div>
      </aside>
    </>
  );
}
