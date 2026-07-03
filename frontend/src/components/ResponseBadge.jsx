import { RESPONSE_META } from "../constants.js";

// Small colored pill labelling the kind of assistant reply (Factual / Facts
// only / Out of scope / No source / Privacy / Service issue).
export default function ResponseBadge({ type }) {
  const meta = RESPONSE_META[type] || RESPONSE_META.FACTUAL;
  return (
    <span className={`badge badge--${meta.tone}`} aria-label={meta.aria}>
      {meta.label}
    </span>
  );
}
