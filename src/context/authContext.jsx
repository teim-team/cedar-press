/**
 * PURPOSE
 * The standalone site's stand-in for the app's AuthProvider.
 *
 * The real accounts live with the app's backend and arrive with a Tribal
 * Business News subscription. Until press accounts move behind real
 * endpoints, this provider answers the same contract the pages read —
 * { user, loading, login, logout, refreshSession } — from two preview
 * accounts and localStorage. Swapping in the real thing means replacing
 * this file with the app's provider and leaving every page unchanged.
 *
 * The user shape carries `workspace_tier` because that is what
 * workspaceTier.js resolveTier reads; one account per press tier so the
 * standard shelf and the Cedar Press+ shelf can both be shown.
 */
import { createContext, useState } from "react";

export const AuthContext = createContext(null);

const SESSION_KEY = "cedar-press-session";

/** The preview accounts. Hand these to anyone who should see the mockup. */
export const DEMO_ACCOUNTS = Object.freeze([
  Object.freeze({
    email: "press@cedarpress.ai",
    password: "cedar-demo-2026",
    workspace_tier: "press",
  }),
  Object.freeze({
    email: "press-plus@cedarpress.ai",
    password: "cedar-demo-2026",
    workspace_tier: "press_pro",
  }),
]);

function readSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);
    return session && typeof session.email === "string" ? session : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readSession);

  const login = async ({ email, password }) => {
    const normalized = String(email || "").trim().toLowerCase();
    const account = DEMO_ACCOUNTS.find(
      (candidate) => candidate.email === normalized && candidate.password === password,
    );
    if (!account) {
      throw new Error(
        "That sign-in did not work. This preview accepts only the preview account shown below.",
      );
    }
    const session = { email: account.email, workspace_tier: account.workspace_tier };
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } catch {
      /* private windows still get a session for this page load */
    }
    setUser(session);
    return session;
  };

  const logout = async () => {
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch {
      /* nothing to clear */
    }
    setUser(null);
  };

  const refreshSession = async () => {
    setUser(readSession());
  };

  // Session reads are synchronous here, so the page is never in the app's
  // "waiting on /me" state.
  const value = { user, loading: false, login, logout, refreshSession };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
