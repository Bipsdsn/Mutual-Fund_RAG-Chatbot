import { IconChat, IconArrow } from "./Icons.jsx";

// Empty-state welcome: centered intro (scope, facts-only) + full-width example
// rows that auto-fill and send. Schemes come live from /api/meta (real data).
export default function Welcome({ meta, examples, onExample, disabled }) {
  const schemes = meta?.schemes || [];

  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <div className="welcome__head">
        <span className="welcome__icon" aria-hidden="true">
          <IconChat width={26} height={26} />
        </span>
        <h2 id="welcome-title" className="welcome__title">
          Ask about HDFC Mutual Fund schemes
        </h2>
        <p className="welcome__lead">
          I share verified facts — expense ratios, lock-in, NAV, exit load, taxes
          — with a source link for every answer. I don&apos;t give investment
          advice, opinions, or predictions.
        </p>
      </div>

      {schemes.length > 0 && (
        <div className="welcome__block">
          <p className="welcome__label">Covered schemes</p>
          <ul className="chip-row" aria-label="Covered schemes">
            {schemes.map((s) => (
              <li key={s} className="chip chip--static">{s}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="welcome__block">
        <p className="welcome__label">Try an example</p>
        <ul className="example-list" aria-label="Example questions">
          {examples.map((q) => (
            <li key={q}>
              <button
                type="button"
                className="example-row"
                onClick={() => onExample(q)}
                disabled={disabled}
              >
                <span className="example-row__text">{q}</span>
                <span className="example-row__arrow" aria-hidden="true">
                  <IconArrow />
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
