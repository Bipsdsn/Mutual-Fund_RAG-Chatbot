// Animated "assistant is thinking" indicator shown while a query is in flight.
export default function TypingIndicator() {
  return (
    <div className="msg msg--assistant">
      <div className="msg__bubble msg__bubble--assistant tone--factual typing" aria-hidden="true">
        <span className="typing__dot" />
        <span className="typing__dot" />
        <span className="typing__dot" />
      </div>
    </div>
  );
}
