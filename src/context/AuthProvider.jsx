/**
 * The session provider.
 *
 * Its own file because a module that exports both a component and the
 * constants beside it breaks fast refresh; the context lives in
 * authContext.js, and this holds only the component.
 *
 * The session is the platform's: `/me` on mount, `/auth/login` to sign in,
 * cookies carrying it, and the subscription's tier arriving from the
 * database. Where there is no API to ask (the public site, or a dev server
 * with no `VITE_API_URL`) nobody is signed in, and there is nothing to wait
 * for.
 *
 * WHEN THE SERVICE DOES NOT ANSWER
 * The session check has a deadline (api.js). An unreachable service is not
 * a signed-out reader, but the page cannot wait on it forever either: it
 * shows the signed-out page with a notice saying the sign-in could not be
 * checked, and a Retry (`sessionUnreachable`, `retrySession`). Before the
 * deadline a stalled check left the page blank for as long as the browser
 * held the connection (40 s and more on Slow 3G, 2026-10-04 audit).
 */
import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";

import * as api from "../api.js";
import { isConnected } from "../config.js";
import { EVENT, identify, track, trackError } from "../features/grove/telemetry.js";
import { AuthContext } from "./authContext.js";

export function AuthProvider({ children }) {
  // Connected, nothing is known until /me answers.
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(() => isConnected());
  // The last check did not reach the service (timeout or dropped connection).
  const [sessionUnreachable, setSessionUnreachable] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const refreshSession = useCallback(async () => {
    if (!isConnected()) return;
    try {
      const session = await api.fetchSession();
      setUser(session);
      identify(session);
      setSessionUnreachable(false);
    } catch (error) {
      trackError(error, { at: "refreshSession" });
      setUser(null);
      setSessionUnreachable(api.isUnreachable(error));
    } finally {
      setLoading(false);
    }
  }, []);

  // The notice's Retry: the page stays as it is while the check runs again.
  const retrySession = useCallback(async () => {
    setRetrying(true);
    try {
      await refreshSession();
    } finally {
      setRetrying(false);
    }
  }, [refreshSession]);

  // Back online is the moment a failed check is worth repeating unasked.
  useEffect(() => {
    if (!sessionUnreachable) return undefined;
    window.addEventListener("online", retrySession);
    return () => window.removeEventListener("online", retrySession);
  }, [sessionUnreachable, retrySession]);

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
        // signed out for this load, but report it rather than swallow it,
        // and tell the reader, with a Retry.
        trackError(error, { at: "session" });
        setUser(null);
        setSessionUnreachable(api.isUnreachable(error));
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
    try {
      const session = await api.login({ email: normalized, password });
      setSessionUnreachable(false);
      setUser(session);
      identify(session);
      track(EVENT.signedIn, { tier: session?.workspace_tier });
      return session;
    } catch (error) {
      track(EVENT.signInFailed, { code: error?.code });
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    if (isConnected()) {
      await api.logout().catch((error) => trackError(error, { at: "logout" }));
    }
    setSessionUnreachable(false);
    setUser(null);
    identify(null);
    track(EVENT.signedOut);
  }, []);

  const value = { user, loading, login, logout, refreshSession, sessionUnreachable, retrySession };
  // The notice is portalled to <body>, outside #root, and that is
  // load-bearing: scripts/prerender.mjs captures #root, and its headless
  // browser cannot reach a production API (no CORS for its origin), so a
  // notice inside #root would be baked into the static door every visitor
  // receives.
  const notice = sessionUnreachable && !user && typeof document !== "undefined"
    ? createPortal(
      <div className="teim-rd teim-rd--paper cp-netnote" role="alert" data-testid="session-unreachable">
        <p>
          Cedar Press could not be reached to check your sign-in, so this is the signed-out page.{" "}
          <button type="button" className="cp-retry" onClick={retrySession} disabled={retrying}>
            {retrying ? "Checking…" : "Retry"}
          </button>
        </p>
      </div>,
      document.body,
    )
    : null;
  return (
    <AuthContext.Provider value={value}>
      {notice}
      {children}
    </AuthContext.Provider>
  );
}
