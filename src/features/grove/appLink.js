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
 * Where "Cedar Grove" goes from Press: the product's page on lumecon.ai.
 *
 * Not into the app. Press and Grove share the data and nothing else a reader
 * can use: a Press subscriber has no Grove account to land in, and the
 * articles the reader came for are here. The marketing page says what Grove
 * is and how to ask for it, which is the only thing a link from Press can
 * honestly offer. The platform links ("Open the platform") stay on `appUrl`,
 * because those do lead to an account the reader holds.
 */
export const GROVE_MARKETING_URL = "https://lumecon.ai/cedar-grove";

/**
 * The research desk's address, with the subject line that says which page the
 * message came from. One spelling of the address for the ten places that
 * write to it; a typo in one of them was a message nobody received.
 */
export const CONTACT_EMAIL = "contact@lumecon.ai";

export function contactHref(subject, body = null) {
  const query = `subject=${encodeURIComponent(subject)}`;
  // A PREFILLED BODY IS THE INTAKE.
  //
  // The request pages ask for a specific set of things and then hand the
  // reader an empty mail window, which is where the specificity goes to die:
  // a request that arrives as one paragraph has to be taken apart by a
  // person before it can be answered. There is no form backend to post to,
  // and pretending otherwise would be worse, so the mail draft carries the
  // questions in order and the reader fills them in.
  return body
    ? `mailto:${CONTACT_EMAIL}?${query}&body=${encodeURIComponent(body)}`
    : `mailto:${CONTACT_EMAIL}?${query}`;
}
