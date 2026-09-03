/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The standalone sign-in. A demo gate, and that is the whole claim.
 *
 * WHAT THIS IS NOT
 * It is not access control. A standalone build is a static site: every byte
 * of it — this module, the account record it reads, the hash inside that
 * record — is downloaded by anyone who asks for the page, and a check that
 * runs in the reader's own browser is a check the reader can delete. Nothing
 * here stops a determined visitor, and no copy on the page may suggest it
 * does. What it does is keep the preview shut to a casual visitor and give a
 * named reviewer a way in, on a deployment that has no server to ask.
 *
 * That is only defensible because nothing behind the gate is confidential.
 * The standalone bundle carries the catalog, the methods, the release history
 * and ten sampled rows per table (public/data/cedar/samples/*__10.csv). The
 * collections themselves are not in it. If that ever stops being true, this
 * module stops being an acceptable answer and the deployment has to connect.
 *
 * WHAT IT DOES PROTECT
 * The password itself. The account arrives as a salted SHA-256 digest, so the
 * reviewer's password is not sitting in a public file even though the digest
 * is. An offline attack on a known salt and a known digest is trivial, so the
 * password must be one issued for this preview and used nowhere else.
 *
 * WHERE THE ACCOUNT COMES FROM
 * `VITE_PRESS_DEMO_ACCOUNTS`, read at build time, in the shape
 * `server/cedar_press/session.py` already reads `CEDAR_PRESS_ACCOUNTS` in —
 * and for the same stated reason, that no credential is committed to the
 * repository and a deployment without one authenticates nobody:
 *
 *     {"reader@example.org": {"salt": "…", "hash": "…", "tier": "press_pro"}}
 *
 * `hash` is the lowercase hex SHA-256 of `"<salt>:<password>"`.
 * `hashPressDemoPassword` is the one definition of that, so the generator
 * (scripts/press-demo-account.mjs) and the check below cannot drift apart.
 *
 * Empty by default. A build configured with nothing signs nobody in, and the
 * gate says sign-in is unavailable rather than showing a form that can only
 * fail.
 *
 * WHAT REPLACES IT
 * `isConnected()`. A connected deployment authenticates against
 * `POST /auth/login` and the signed, HTTP-only cookie in
 * `server/cedar_press/session.py`; this gate switches itself off, because
 * every flag below is gated on `!isConnected()` rather than on a second
 * switch somebody has to remember to flip.
 */

import { isConnected } from "../../config.js";

/** The build-time variable an operator sets. Named here so messages can say it. */
export const PRESS_DEMO_ACCOUNTS_VAR = "VITE_PRESS_DEMO_ACCOUNTS";

/**
 * Tiers a demo account may claim. Mirrors `PRESS_TIERS` in
 * `server/cedar_press/press_catalog.py`. A record naming anything else is
 * dropped rather than coerced: a configuration typo must not be the thing
 * that decides what a reader can open.
 */
const DEMO_TIERS = Object.freeze(["press", "press_pro"]);

/**
 * Parse the configured accounts.
 *
 * Unparseable configuration yields no accounts rather than a guess. A record
 * that is individually invalid is dropped, so one bad row cannot lock out the
 * rest, but a record is only valid if it is unmistakably a hash: 64 hex
 * characters, never a password somebody pasted into the wrong field.
 */
export function parsePressDemoAccounts(raw) {
  const text = String(raw ?? "").trim();
  if (!text) return Object.freeze([]);
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    return Object.freeze([]);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return Object.freeze([]);
  }
  const accounts = [];
  for (const [email, record] of Object.entries(parsed)) {
    if (!record || typeof record !== "object") continue;
    const salt = typeof record.salt === "string" ? record.salt : "";
    const hash = typeof record.hash === "string" ? record.hash.trim().toLowerCase() : "";
    const tier = typeof record.tier === "string" ? record.tier : "press";
    const key = String(email).trim().toLowerCase();
    if (!key || !salt || !/^[0-9a-f]{64}$/.test(hash)) continue;
    if (!DEMO_TIERS.includes(tier)) continue;
    accounts.push(Object.freeze({ email: key, salt, hash, workspace_tier: tier }));
  }
  return Object.freeze(accounts);
}

/**
 * The accounts this build was configured with. Empty unless one was set.
 *
 * Read by its literal name and not through `PRESS_DEMO_ACCOUNTS_VAR`: Vite
 * substitutes `import.meta.env.VITE_*` textually at build time, so a computed
 * lookup would resolve to nothing in the very build this exists for.
 */
export const PRESS_DEMO_ACCOUNTS = parsePressDemoAccounts(
  import.meta.env?.VITE_PRESS_DEMO_ACCOUNTS ?? "",
);

/**
 * Whether the demo gate is the thing checking passwords on this deployment.
 *
 * False the moment the deployment connects — the platform's session takes
 * over and this must not stand beside it — and false when nothing was
 * configured, which is what makes "a build with no account signs nobody in"
 * a property of the code rather than a promise in a comment.
 */
export const PRESS_DEMO_GATE_ACTIVE = !isConnected() && PRESS_DEMO_ACCOUNTS.length > 0;

/** Whether the gate may show a sign-in form at all. */
export const PRESS_SIGN_IN_AVAILABLE = isConnected() || PRESS_DEMO_GATE_ACTIVE;

/**
 * What the reader is told when the demo gate is what let them in. It says the
 * true thing: the check ran in their browser, on a build with no server.
 */
// PRESS_DEMO_NOTICE was removed 2026-09-02. It rendered "Preview build.
// Nothing runs behind this site..." on the sign-in panel, and the owner's
// judgement was that a reader he has already briefed does not need the
// service explaining itself to them.
//
// The fact it stated has not changed and is not hidden: this gate is checked
// in the reader's own browser, everything it reads is in a bundle they have
// already downloaded, and it is therefore a demonstration gate rather than
// access control. That is in this module's docstring above, and SECURITY.md
// puts it out of scope as a vulnerability while keeping "a record reachable
// through it that should not be public" in scope. The safety property was
// never the paragraph - it is that nothing confidential sits behind the gate.

/** What the gate says when nobody configured an account for this build. */
export const PRESS_DEMO_UNCONFIGURED =
  "Sign-in is not available yet.";

const HEX = "0123456789abcdef";

function toHex(bytes) {
  let out = "";
  for (const byte of bytes) out += HEX[byte >> 4] + HEX[byte & 15];
  return out;
}

/**
 * The digest a configured record must carry: lowercase hex SHA-256 of
 * `"<salt>:<password>"`.
 *
 * `subtle` is injectable so the generator script and the tests run the same
 * function the browser does rather than a second copy of the recipe.
 */
export async function hashPressDemoPassword(salt, password, subtle = globalThis.crypto?.subtle) {
  if (!subtle) {
    // Only reachable on an insecure origin: WebCrypto is not exposed outside
    // a secure context. Said plainly, because "sign-in failed" would send the
    // reader looking for a password problem they do not have.
    throw new Error(
      "This preview sign-in needs a secure connection (https, or localhost) and this page is not on one.",
    );
  }
  const encoded = new TextEncoder().encode(`${String(salt)}:${String(password)}`);
  return toHex(new Uint8Array(await subtle.digest("SHA-256", encoded)));
}

/**
 * Compare two digests without returning early on the first differing byte.
 *
 * Worth saying plainly: this buys nothing here. The attacker already has the
 * digest — it is in the bundle — so there is no timing channel left to close.
 * It is written this way because `session.py` compares with `compare_digest`
 * and a comparison in the same role should not teach the next reader a looser
 * habit.
 */
function equalDigest(a, b) {
  if (a.length !== b.length) return false;
  let difference = 0;
  for (let i = 0; i < a.length; i += 1) difference |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return difference === 0;
}

/**
 * Verify a sign-in against the configured accounts.
 *
 * Returns the session payload the pages already read — `{ email,
 * workspace_tier }`, the shape `session.py`'s `as_payload` returns and
 * `workspaceTier.js` resolves entitlement from — or null. Null covers every
 * failure, including the one that matters most: no accounts were configured,
 * so there is nothing any password can match.
 */
export async function verifyPressDemoAccount(
  { email, password } = {},
  accounts = PRESS_DEMO_ACCOUNTS,
  subtle = globalThis.crypto?.subtle,
) {
  const key = String(email ?? "").trim().toLowerCase();
  const secret = String(password ?? "");
  if (!key || !secret || !accounts.length) return null;
  const account = accounts.find((candidate) => candidate.email === key);
  if (!account) return null;
  const digest = await hashPressDemoPassword(account.salt, secret, subtle);
  if (!equalDigest(digest, account.hash)) return null;
  return { email: account.email, workspace_tier: account.workspace_tier };
}
