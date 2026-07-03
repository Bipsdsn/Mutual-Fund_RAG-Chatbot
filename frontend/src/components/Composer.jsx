import { useEffect, useRef, useState } from "react";
import { IconSearch, IconSend } from "./Icons.jsx";

const MAX_LEN = 2000;

// Pill-shaped composer (Stitch style): leading search icon, growing textarea,
// trailing circular teal send button. Enter sends, Shift+Enter = newline.
export default function Composer({ onSend, loading }) {
  const [value, setValue] = useState("");
  const taRef = useRef(null);

  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [value]);

  useEffect(() => {
    if (!loading) taRef.current?.focus();
  }, [loading]);

  const canSend = value.trim().length > 0 && !loading;

  function submit(e) {
    e?.preventDefault();
    if (!canSend) return;
    onSend(value);
    setValue("");
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form className="composer" onSubmit={submit}>
      <label htmlFor="composer-input" className="sr-only">
        Ask a question about HDFC Mutual Fund schemes
      </label>
      <div className="composer__field">
        <span className="composer__lead" aria-hidden="true">
          <IconSearch />
        </span>
        <textarea
          id="composer-input"
          ref={taRef}
          className="composer__input"
          placeholder="Ask about expense ratio, lock-in, NAV, exit load…"
          value={value}
          maxLength={MAX_LEN}
          rows={1}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={loading}
          aria-describedby="composer-hint"
        />
        <button
          type="submit"
          className="composer__send"
          disabled={!canSend}
          aria-label="Send question"
        >
          <IconSend width={20} height={20} />
        </button>
      </div>
      <span id="composer-hint" className="sr-only">
        Press Enter to send, Shift plus Enter for a new line.
      </span>
    </form>
  );
}
