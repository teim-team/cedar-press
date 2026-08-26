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
import { createContext } from "react";

export const AuthContext = createContext(null);

export const SESSION_KEY = "cedar-press-session";

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

/** The stored session, or null when there is none to read. */
export function readSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);
    return session && typeof session.email === "string" ? session : null;
  } catch {
    return null;
  }
}

/** Persist a preview session. Standalone only: connected, the cookie is it. */
export function storeSession(session) {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // Private windows still get a session for this page load.
  }
}

export function clearStoredSession() {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    // Nothing to clear.
  }
}
