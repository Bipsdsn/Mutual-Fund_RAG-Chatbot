import { useEffect, useRef } from "react";
import Message from "./Message.jsx";
import TypingIndicator from "./TypingIndicator.jsx";

// Scrollable conversation transcript. aria-live=polite announces new assistant
// answers to screen readers; auto-scrolls to the latest message.
export default function MessageList({ messages, loading }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  return (
    <div
      className="messages"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
      aria-label="Conversation"
    >
      {messages.map((m) => (
        <Message key={m.id} message={m} />
      ))}
      {loading && <TypingIndicator />}
      <div ref={endRef} />
    </div>
  );
}
