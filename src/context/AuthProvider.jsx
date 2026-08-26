/**
 * The session provider.
 *
 * Its own file because a module that exports both a component and the
 * constants beside it breaks fast refresh; the context and the preview
 * account records live in authContext.js, and this holds only the component.
 *
 * TWO MODES, ONE CONTRACT
 * Connected, the session is the platform's: `/me` on mount, `/auth/login`
 * to sign in, cookies carrying it, and the subscription's tier arriving
 * from the database. Standalone, the same contract is served from the
 * preview accounts so the service can be demonstrated and reviewed on its
 * own. Pages never learn which mode they are in — they read `user`,
 * `loading`, `login`, `logout` and `refreshSession` either way — so
 * connecting a deployment is configuration, not a rewrite.
 */
import { useCallback, useEffect, useState } from "react";

import * as api from "../api.js";
import { isConnected } from "../config.js";
import { EVENT, identify, track, trackError } from "../features/grove/telemetry.js";
import {
  AuthContext,
  PREVIEW_ACCOUNTS,
  clearStoredSession,
  readSession,
  storeSession,
} from "./authContext.js";

export function AuthProvider({ children }) {
  // Connected, nothing is known until /me answers; standalone, the stored
  // session is known synchronously and the gate must not flash.
  const [user, setUser] = useState(() => (isConnected() ? null : readSession()));
  const [loading, setLoading] = useState(() => isConnected());

  const refreshSession = useCallback(async () => {
    if (!isConnected()) {
      setUser(readSession());
      return;
    }
    try {
      const session = await api.fetchSession();
      setUser(session);
      identify(session);
    } catch (error) {
      trackError(error, { at: "refreshSession" });
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // The first read of the session, connected only. Aborted on unmount so a
  // slow answer cannot land on a provider that is gone, and awaited rather
  // than called synchronously so the effect does not cascade a render.
  useEffect(() => {
    if (!isConnected()) return undefined;
    const controller = new AbortController();
    let live = true;
    (async () => {
      try {
        const session = await api.fetchSession({ signal: controller.signal });
        if (!live) return;
        setUser(session);
        identify(session);
      } catch (error) {
        if (!live || error?.name === "AbortError") return;
        // An unreachable service is not a signed-out reader: keep them
        // signed out for this load, but report it rather than swallow it.
        trackError(error, { at: "session" });
        setUser(null);
      } finally {
        if (live) setLoading(false);
      }
    })();
    return () => {
      live = false;
      controller.abort();
    };
  }, []);

  const login = useCallback(async ({ email, password }) => {
    const normalized = String(email || "").trim().toLowerCase();
    if (isConnected()) {
      try {
        const session = await api.login({ email: normalized, password });
        setUser(session);
        identify(session);
        track(EVENT.signedIn, { tier: session?.workspace_tier });
        return session;
      } catch (error) {
        track(EVENT.signInFailed, { code: error?.code });
        throw error;
      }
    }
    const account = PREVIEW_ACCOUNTS.find(
      (candidate) => candidate.email === normalized && candidate.password === password,
    );
    if (!account) {
      track(EVENT.signInFailed, { code: "INVALID_CREDENTIALS" });
      throw new Error(
        "That sign-in did not work. Check the address and password on your Cedar Press confirmation.",
      );
    }
    const session = { email: account.email, workspace_tier: account.workspace_tier };
    storeSession(session);
    setUser(session);
    identify(session);
    track(EVENT.signedIn, { tier: session.workspace_tier });
    return session;
  }, []);

  const logout = useCallback(async () => {
    if (isConnected()) {
      await api.logout().catch((error) => trackError(error, { at: "logout" }));
    }
    clearStoredSession();
    setUser(null);
    identify(null);
    track(EVENT.signedOut);
  }, []);

  const value = { user, loading, login, logout, refreshSession };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
