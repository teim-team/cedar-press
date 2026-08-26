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
 *
 * Which screen opens is what this browser did last time. Someone who has
 * already activated should not be asked for a code they have spent.
 */

const SEEN_KEY = "lumecon.press.hasAccount";

/**
 * Whether the activation flow may be offered at all.
 *
 * The client contract (POST /auth/press/validate, POST /auth/press/activate)
 * has no server handlers yet, so a reachable activation form would walk every
 * subscriber to a 404 after they typed their code. Until the routes exist the
 * gate offers sign-in only, and provisioning stays where it is today: accounts
 * are created for subscribers (scripts/invite-account.js and the seed
 * scripts), with Tribal Business News owning issuance. Flip this to true in
 * the commit that lands the server routes, and nowhere else.
 */
export const PRESS_ACTIVATION_AVAILABLE = false;

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
 * Which screen to open with. A browser that has activated opens on sign-in;
 * everything else opens on activation, because someone arriving from a Tribal
 * Business News confirmation has a code in hand and no account yet.
 */
export function initialPressStep(storage) {
  // With no server routes behind activation, sign-in is the only screen the
  // gate may open on; the storage hint matters again when activation ships.
  if (!PRESS_ACTIVATION_AVAILABLE) return PRESS_STEP.SIGN_IN;
  try {
    return storage?.getItem(SEEN_KEY) === "1" ? PRESS_STEP.SIGN_IN : PRESS_STEP.ACTIVATE;
  } catch {
    // Private browsing and blocked storage both throw here. Activation is the
    // safe default: it is the screen that can still reach the other in a click.
    return PRESS_STEP.ACTIVATE;
  }
}

/**
 * Whether this browser has signed in to (or activated) a Cedar Press account
 * before. The gate's plans-or-log-in switch opens on the likely side: a
 * remembered account lands on Log in, everyone else sees the plans first.
 * Distinct from initialPressStep, which decides which sign-in screen opens,
 * not which side of the switch does.
 */
export function hasPressAccount(storage) {
  try {
    return storage?.getItem(SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

/** Remember that this browser has activated, so the next visit opens on sign-in. */
export function rememberPressAccount(storage) {
  try {
    storage?.setItem(SEEN_KEY, "1");
  } catch {
    // Nothing to do: the gate still works, it just opens on activation again.
  }
}

/**
 * What to say when activation fails. The server's codes are deliberately
 * distinct, because "we have never seen this code" and "this code was already
 * used" need different next steps from the reader.
 */
export function pressSignupError(code, fallback) {
  switch (code) {
    case "PRESS_CODE_INVALID":
      return "That code was not recognized. Check it against your Tribal Business News confirmation, including the letter O against the digit 0.";
    case "PRESS_CODE_USED":
      return "That code has already been activated. Each code is issued to one authorized user, so sign in instead, or reset the password if you do not have it.";
    case "PRESS_CODE_EXPIRED":
      return "That code has expired. Tribal Business News can issue a new one with your membership.";
    case "PRESS_CODE_EMAIL_MISMATCH":
      return "That code was issued to a different address. Use the address on your Tribal Business News membership.";
    case "EMAIL_IN_USE":
      return "There is already an account with that address. Sign in instead.";
    default:
      return fallback || "That did not work. Check the details and try again.";
  }
}
