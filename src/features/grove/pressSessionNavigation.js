/** Canonical public-door handoff; preview hosts keep their local test gate. */
const PUBLIC_HOSTS = new Set(["cedarpress.ai", "www.cedarpress.ai"]);
export const PRESS_WORKSPACE_ORIGIN = "https://app.cedarpress.ai";

export function workspaceSignInHref(location) {
  if (!location || location.protocol !== "https:" || !PUBLIC_HOSTS.has(location.hostname)) return null;
  const destination = new URL("/", PRESS_WORKSPACE_ORIGIN);
  destination.searchParams.set("signin", "1");
  const collection = new URLSearchParams(location.search || "").get("collection");
  if (collection && /^[a-z][a-z0-9-]{0,63}$/.test(collection)) {
    destination.searchParams.set("collection", collection);
  }
  return destination.href;
}

export function requestedSignIn(search) {
  return new URLSearchParams(search || "").get("signin") === "1";
}
