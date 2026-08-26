/**
 * The session provider.
 *
 * Its own file because a module that exports both a component and the
 * constants beside it breaks fast refresh; the context and the account
 * records live in authContext.js, and this holds only the component.
 */
import { useState } from "react";

import { AuthContext, PREVIEW_ACCOUNTS, SESSION_KEY, readSession } from "./authContext.js";

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
