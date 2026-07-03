import { DISCLAIMER } from "../constants.js";

// App header: mobile menu button (opens sidebar), product identity, an
// always-visible facts-only disclaimer badge, and a freshness line.
export default function Header({ meta, onMenu }) {
  return (
    <header className="app-header" role="banner">
      <div className="app-header__left">
        <button
          type="button"
          className="app-header__menu"
          onClick={onMenu}
          aria-label="Open chat history"
        >
          <span aria-hidden="true">☰</span>
        </button>
        <div className="app-header__brand">
          <span className="app-header__mark" aria-hidden="true">MF</span>
          <div className="app-header__titles">
            <h1 className="app-header__title">HDFC Mutual Fund — FAQ Assistant</h1>
            <p className="app-header__subtitle">
              Answers only from official sources
              {meta?.scrape_date ? ` · updated ${meta.scrape_date}` : ""}
            </p>
          </div>
        </div>
      </div>
      <span className="disclaimer-badge" role="note" aria-label={DISCLAIMER}>
        <span className="disclaimer-badge__dot" aria-hidden="true" />
        {DISCLAIMER}
      </span>
    </header>
  );
}
