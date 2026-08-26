/**
 * PURPOSE
 * The standalone site's stand-in for the app's auth.
 *
 * Cedar Press is a mockup right now: the real accounts live with the app's
 * backend and arrive with a Tribal Business News subscription or a Cedar
 * Grove license. Until press accounts move behind real endpoints, this module
 * answers the same two questions the app's useAuth answers — who is signed in,
 * and did this sign-in work — from one preview account and localStorage.
 *
 * Swapping in the real thing later means replacing signIn() with the API call
 * and leaving every caller unchanged; the session shape ({ email, tier })
 * matches what the app's pressAccess model reads.
 */

const SESSION_KEY = "cedar-press-session";

/**
 * The preview account. Hand these credentials to anyone who should see the
 * mockup; they are intentionally printed on the sign-in page as well, because
 * a preview that people cannot get into demonstrates nothing.
 */
export const DEMO_ACCOUNT = Object.freeze({
  email: "press@cedarpress.ai",
  password: "cedar-demo-2026",
  tier: "press",
});

export function currentSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);
    return session && typeof session.email === "string" ? session : null;
  } catch {
    return null;
  }
}

export async function signIn({ email, password }) {
  const normalized = String(email || "").trim().toLowerCase();
  if (normalized !== DEMO_ACCOUNT.email || password !== DEMO_ACCOUNT.password) {
    throw new Error(
      "That sign-in did not work. Use the preview account shown below.",
    );
  }
  const session = { email: DEMO_ACCOUNT.email, tier: DEMO_ACCOUNT.tier };
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    /* private windows still get a session for this page load */
  }
  return session;
}

export function signOut() {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    /* nothing to clear */
  }
}
