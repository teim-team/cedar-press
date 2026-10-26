import { PUBLIC_HOSTS } from "../../config.js";
import { PRESS_LOGIN_PATH } from "./pressRoutes.js";

/** Canonical public-door handoff; preview hosts keep their local test gate. */
export function workspaceSignInHref(location) {
  if (!location || location.protocol !== "https:" || !PUBLIC_HOSTS.has(location.hostname)) return null;
  return `https://app.cedarpress.ai${PRESS_LOGIN_PATH}`;
}

/** The membership cards, on the same host as the login page. */
export function subscribeHref(location = globalThis.location) {
  return workspaceSignInHref(location) ? "https://app.cedarpress.ai/subscribe" : "/subscribe";
}

/** The workspace host serves the app; VITE_APP_HOST=1 does the same for a local dev server. */
export function isWorkspaceHost(location) {
  return location?.hostname === "app.cedarpress.ai" || import.meta.env?.VITE_APP_HOST === "1";
}

/** A same-origin path, or "/". Anything that could leave the site is dropped. */
export function safeNext(raw) {
  const value = String(raw ?? "");
  // Browsers drop tabs and newlines from a URL, so "/\t/host" becomes "//host".
  return /^\/(?![/\\])[^\s\\]*$/.test(value) && !value.startsWith(PRESS_LOGIN_PATH) ? value : "/";
}

/** Where a signed-out visitor on the workspace host is sent, remembering where they were going. */
export function loginRedirect(location) {
  const here = `${location.pathname}${location.search}`;
  const next = safeNext(here);
  return next === "/" ? PRESS_LOGIN_PATH : `${PRESS_LOGIN_PATH}?next=${encodeURIComponent(next)}`;
}
