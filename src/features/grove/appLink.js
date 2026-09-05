/**
 * PURPOSE
 * Where "open the app" goes when Cedar Press stands alone.
 *
 * Inside teim-app these were client-side routes (/app, /app/grove, the plan
 * page). On cedarpress.ai the app is another origin, so the links become
 * absolute. VITE_APP_URL names the app's origin at build time, the same
 * arrangement the marketing site uses with PUBLIC_APP_URL; without it the
 * links land on lumecon.ai, which can hand the visitor onward.
 */

const APP_ORIGIN = (import.meta.env?.VITE_APP_URL || "https://lumecon.ai").replace(/\/+$/, "");

/** An absolute URL into the app, from the app-relative path the page names. */
export function appUrl(path = "") {
  return `${APP_ORIGIN}${path}`;
}

/**
 * The research desk's address, with the subject line that says which page the
 * message came from. One spelling of the address for the ten places that
 * write to it; a typo in one of them was a message nobody received.
 */
export const CONTACT_EMAIL = "contact@lumecon.ai";

export function contactHref(subject) {
  return `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}`;
}
