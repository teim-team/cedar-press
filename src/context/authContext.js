/**
 * PURPOSE
 * The session context: who is signed in, and what their subscription
 * includes.
 *
 * The contract the pages read is { user, loading, login, logout,
 * refreshSession, sessionUnreachable, retrySession }. The session is the
 * platform API's (a signed, HTTP-only cookie); nothing about it is kept in
 * browser storage. The shape carries `workspace_tier` because
 * workspaceTier.js resolves entitlement from it.
 *
 * Subscriber accounts are provisioned through Tribal Business News; there is
 * deliberately no self-serve account creation here, because an account exists
 * because an entitlement does.
 */
import { createContext } from "react";

export const AuthContext = createContext(null);
