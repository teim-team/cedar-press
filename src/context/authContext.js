/**
 * The session context: { user, loading, login, logout, refreshSession,
 * sessionUnreachable, retrySession }. The session is a signed HTTP-only
 * cookie; nothing is kept in browser storage. Accounts are created from the
 * emailed setup link that follows a Stripe checkout.
 */
import { createContext } from "react";

export const AuthContext = createContext(null);
