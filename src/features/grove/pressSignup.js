/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The Cedar Press way in, as logic the gate can render and tests can pin.
 *
 * Cedar Press is standalone and annual. An eligible Tribal Business News
 * membership issues an access code; the code establishes the entitlement; the
 * account follows. Tribal Business News owns payment, renewals, upgrades and
 * issuance. From here the only question is whether this person currently
 * holds an eligible entitlement.
 *
 * Activation is two steps on purpose. Step one asks for the code and an email
 * address and nothing else, so the first screen is two fields rather than
 * four. A password is only worth choosing once the code has been accepted.
 */

import { isConnected } from "../../config.js";

/**
 * Whether the activation flow may be offered at all.
 *
 * The routes exist now (POST /press/activation/validate, POST
 * /press/activation), so this is no longer a constant somebody has to
 * remember to flip. It is whether this deployment can reach them.
 *
 * That distinction matters because the two deployments are real. A connected
 * build talks to the API and can validate a code; the standalone build —
 * which is what cedarpress.ai serves today, a static site with no backend —
 * cannot. Offering a code field there would take a subscriber's code, fail
 * every call, and tell them their membership does not work. Sign-in only is
 * the honest surface for a build with nothing behind it.
 *
 * Deliberately not a check that "the API said activation is on". A deployment
 * that cannot make the call cannot ask either.
 */
export const PRESS_ACTIVATION_AVAILABLE = isConnected();

export const PRESS_STEP = Object.freeze({
  /** Step one of activation: the access code and an email address. */
  ACTIVATE: "activate",
  /** Step two: choose a password, reached only after the code is accepted. */
  SET_PASSWORD: "set-password",
  /** A reader who has already activated. */
  SIGN_IN: "sign-in",
});

/**
 * Codes are issued by Tribal Business News, so this validates shape only: the
 * server decides whether a well-formed code is real, unspent and unexpired.
 * Checking the shape here keeps an obvious typo from costing a round trip and
 * from burning a rate-limit attempt.
 *
 * Accepted: 8 to 32 letters and digits once hyphens and spaces come out. Case
 * and spacing are the reader's problem, not theirs.
 */
export function normalizePressCode(raw) {
  return String(raw ?? "")
    .toUpperCase()
    .replace(/[\s-]+/g, "");
}

export function isPlausiblePressCode(raw) {
  const code = normalizePressCode(raw);
  return code.length >= 8 && code.length <= 32 && /^[A-Z0-9]+$/.test(code);
}

/** Group a code for display, so a long string stays readable while typing. */
export function formatPressCode(raw) {
  const code = normalizePressCode(raw);
  return code.replace(/(.{4})(?=.)/g, "$1-");
}

/**
 * What to say when activation fails. The server's codes are deliberately
 * distinct, because "we have never seen this code" and "this code was already
 * used" need different next steps from the reader. "Used" and "expired" are
 * only ever said to the address a code was issued to; a code paired with any
 * other address reads as not recognized, so the endpoint does not reveal
 * which codes exist.
 */
export function pressSignupError(code, fallback) {
  switch (code) {
    // Also the answer for a real code paired with the wrong address: the
    // server says nothing about a code until the code and the address both
    // match, so this copy has to cover both mistakes.
    case "PRESS_CODE_INVALID":
      return "That code and address do not match a code we issued. Check the code against your Tribal Business News confirmation, including the letter O against the digit 0, and use the address on your membership.";
    case "PRESS_CODE_USED":
      return "That code has already been activated. Each code is issued to one authorized user, so sign in instead, or reset the password if you do not have it.";
    case "PRESS_CODE_EXPIRED":
      return "That code has expired. Tribal Business News can issue a new one with your membership.";
    case "EMAIL_IN_USE":
      return "There is already an account with that address. Sign in instead.";
    default:
      return fallback || "That did not work. Check the details and try again.";
  }
}
