import { useCallback, useEffect, useState } from "react";

const KEY = "mf.theme.v1";

function initialTheme() {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {}
  // Respect the OS preference on first visit.
  if (window.matchMedia?.("(prefers-color-scheme: dark)").matches) return "dark";
  return "light";
}

// Theme state applied to <html data-theme>, persisted to localStorage. Dark mode
// enables the animated starry-sky background.
export function useTheme() {
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(KEY, theme);
    } catch {}
  }, [theme]);

  const toggle = useCallback(
    () => setTheme((t) => (t === "dark" ? "light" : "dark")),
    []
  );

  return { theme, toggle, isDark: theme === "dark" };
}
