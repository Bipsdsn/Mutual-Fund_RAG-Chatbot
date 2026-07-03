import { useState } from "react";
import Header from "./components/Header.jsx";
import Sidebar from "./components/Sidebar.jsx";
import Welcome from "./components/Welcome.jsx";
import MessageList from "./components/MessageList.jsx";
import Composer from "./components/Composer.jsx";
import StarField from "./components/StarField.jsx";
import { useChat } from "./hooks/useChat.js";
import { useTheme } from "./hooks/useTheme.js";
import { DISCLAIMER } from "./constants.js";

export default function App() {
  const {
    sessions,
    currentId,
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
  } = useChat();
  const { isDark, toggle } = useTheme();
  const [navOpen, setNavOpen] = useState(false);

  const started = messages.length > 0;

  const handleSelect = (id) => {
    selectSession(id);
    setNavOpen(false);
  };
  const handleNew = () => {
    newChat();
    setNavOpen(false);
  };

  return (
    <div className="app">
      {/* Animated starry-sky background (visible in dark mode). */}
      {isDark && <StarField />}

      <a href="#composer-input" className="skip-link">
        Skip to question box
      </a>

      <div className="layout">
        <Sidebar
          sessions={sessions}
          currentId={currentId}
          onSelect={handleSelect}
          onNew={handleNew}
          onDelete={deleteSession}
          isDark={isDark}
          onToggleTheme={toggle}
          open={navOpen}
          onClose={() => setNavOpen(false)}
        />

        <div className="column">
          <Header meta={meta} onMenu={() => setNavOpen(true)} />

          <main className="main" role="main">
            <div className="conversation">
              {!started && (
                <Welcome
                  meta={meta}
                  examples={examples}
                  onExample={send}
                  disabled={loading}
                />
              )}

              {started && <MessageList messages={messages} loading={loading} />}

              {error && (
                <div className="error-banner" role="alert">
                  <span>{error}</span>
                  <button
                    type="button"
                    className="error-banner__retry"
                    onClick={retry}
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>
          </main>

          <footer className="composer-bar" role="contentinfo">
            <div className="composer-bar__inner">
              <Composer onSend={send} loading={loading} />
              <p className="composer-bar__disclaimer">{DISCLAIMER}</p>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
