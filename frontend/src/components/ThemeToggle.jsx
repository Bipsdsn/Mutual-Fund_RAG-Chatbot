// Light/dark theme switch. Shows a moon in light mode (tap → go dark) and a sun
// in dark mode (tap → go light).
export default function ThemeToggle({ isDark, onToggle }) {
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={onToggle}
      aria-pressed={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Light mode" : "Dark mode"}
    >
      <span className="theme-toggle__icon" aria-hidden="true">
        {isDark ? "☀" : "☾"}
      </span>
    </button>
  );
}
