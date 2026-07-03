import ResponseBadge from "./ResponseBadge.jsx";
import { IconSpark, IconExternal } from "./Icons.jsx";

// Separates the model/footer text: the backend already appends a freshness line
// and the disclaimer; we strip those so the UI can render them as structured,
// styled chrome instead of raw text (the disclaimer lives in the header).
function splitAnswer(text) {
  const lines = (text || "").split(/\n+/).map((l) => l.trim()).filter(Boolean);
  const body = [];
  for (const line of lines) {
    if (line.startsWith("Last updated from sources:")) continue;
    if (line === "Facts-only. No investment advice.") continue;
    body.push(line);
  }
  return body;
}

function hostLabel(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "source";
  }
}

export default function Message({ message }) {
  if (message.role === "user") {
    return (
      <div className="msg msg--user">
        <div className="msg__bubble msg__bubble--user">{message.text}</div>
      </div>
    );
  }

  const tone = (message.responseType || "FACTUAL").toLowerCase();
  const paragraphs = splitAnswer(message.text);
  const hasFooter = message.sourceUrl || message.lastUpdated;

  return (
    <div className="msg msg--assistant">
      <span className={`msg__avatar tone-bg--${tone}`} aria-hidden="true">
        <IconSpark width={18} height={18} />
      </span>
      <div className={`msg__bubble msg__bubble--assistant tone--${tone}`}>
        <div className="msg__content">
          <div className="msg__meta">
            <ResponseBadge type={message.responseType} />
          </div>
          <div className="msg__body">
            {paragraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </div>

        {hasFooter && (
          <div className="msg__footer">
            {message.sourceUrl && (
              <a
                className="source-link"
                href={message.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                Source: {hostLabel(message.sourceUrl)}
                <span className="source-link__icon" aria-hidden="true">
                  <IconExternal width={14} height={14} />
                </span>
              </a>
            )}
            {message.lastUpdated && (
              <span className="freshness" title="Data freshness">
                Updated {message.lastUpdated}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
