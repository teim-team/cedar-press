/**
 * The session context: { user, loading, login, logout, refreshSession,
 * sessionUnreachable, retrySession }. The session is a signed HTTP-only
 * cookie; nothing is kept in browser storage. There is no self-serve account
 * creation: accounts exist because Tribal Business News issued an entitlement.
 */
import { createContext } from "react";

export const AuthContext = createContext(null);
