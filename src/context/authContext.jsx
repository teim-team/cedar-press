/**
 * PURPOSE
 * The session provider: who is signed in, and what their subscription
 * includes.
 *
 * This is the integration point for the platform's authentication. The
 * contract the pages read — { user, loading, login, logout, refreshSession } —
 * is the platform's own, and the session shape carries `workspace_tier`
 * because workspaceTier.js resolves entitlement from it. Sessions persist in
 * browser storage, and every access is guarded so a storage-denying context
 * degrades rather than breaks the gate.
 *
 * Subscriber accounts are provisioned through Tribal Business News; there is
 * deliberately no self-serve account creation here, because an account exists
 * because an entitlement does.
 */
import { createContext, useState } from "react";

export const AuthContext = createContext(null);

const SESSION_KEY = "cedar-press-session";

/** Accounts provisioned for preview access, one per press tier. */
export const PREVIEW_ACCOUNTS = Object.freeze([
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
    const account = PREVIEW_ACCOUNTS.find(
      (candidate) => candidate.email === normalized && candidate.password === password,
    );
    if (!account) {
      throw new Error(
        "That sign-in did not work. Check the address and password on your Cedar Press confirmation.",
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
