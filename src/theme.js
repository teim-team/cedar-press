/**
 * PURPOSE
 * Light and dark, the same contract as the app: `data-theme="dark"` on the
 * root element switches the token block, a saved choice wins over the system
 * preference, and index.html applies the saved choice before first paint so
 * neither mode flashes.
 */

const THEME_KEY = "cedar-press-theme";

export function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function setTheme(theme) {
  if (theme === "dark") {
    document.documentElement.dataset.theme = "dark";
  } else {
    delete document.documentElement.dataset.theme;
  }
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    /* preference just won't persist */
  }
}
