// The standalone sign-in.
//
// Three of these are the reason the module exists. A configured account gets
// in; a wrong password does not; and a build that was configured with nothing
// signs NOBODY in — which is the property that makes shipping a client-side
// password check defensible at all, because it means a deployment nobody
// provisioned is a deployment with no way past the gate rather than one with
// a convenient fallback.
//
// This suite runs with no VITE_API_URL and no VITE_PRESS_DEMO_ACCOUNTS, so
// the module-level constants are the unconfigured standalone case and are
// asserted as such. Everything else is exercised through the pure functions,
// which take their accounts as an argument precisely so a test does not have
// to reach into a build-time constant to change it.

import assert from "node:assert/strict";
import test from "node:test";

import {
  PRESS_DEMO_ACCOUNTS,
  PRESS_DEMO_ACCOUNTS_VAR,
  PRESS_DEMO_GATE_ACTIVE,
  PRESS_DEMO_UNCONFIGURED,
  PRESS_SIGN_IN_AVAILABLE,
  hashPressDemoPassword,
  parsePressDemoAccounts,
  verifyPressDemoAccount,
} from "./pressDemoGate.js";

const EMAIL = "reader@example.org";
const PASSWORD = "a-password-only-this-test-uses";
const SALT = "0123456789abcdef";

/** One configured account, hashed the way an operator's generator would. */
async function configured({ email = EMAIL, password = PASSWORD, salt = SALT, tier = "press_pro" } = {}) {
  return parsePressDemoAccounts(
    JSON.stringify({
      [email]: { salt, hash: await hashPressDemoPassword(salt, password), tier },
    }),
  );
}

test("the digest is the salted SHA-256 an operator can reproduce", async () => {
  // A fixed vector, so a change to the recipe fails here rather than silently
  // invalidating every account already provisioned — and so an operator can
  // check their own generator against a number rather than against prose.
  // This is sha256("0123456789abcdef:a-password-only-this-test-uses"), the
  // same value node's own createHash produces for those bytes.
  const digest = await hashPressDemoPassword(SALT, PASSWORD);
  assert.equal(digest, "46cc9143b0a644d51c0a75e2b75c3993403778b00724061c08b8208cd3973a93");
  // The salt is what makes two deployments sharing a password differ.
  const other = await hashPressDemoPassword("a-different-salt", PASSWORD);
  assert.notEqual(digest, other);
});

test("a configured account signs in and carries its tier", async () => {
  const accounts = await configured();
  const session = await verifyPressDemoAccount({ email: EMAIL, password: PASSWORD }, accounts);
  assert.deepEqual(session, { email: EMAIL, workspace_tier: "press_pro" });
});

test("the address is matched past case and surrounding space", async () => {
  const accounts = await configured();
  const session = await verifyPressDemoAccount(
    { email: "  Reader@Example.ORG ", password: PASSWORD },
    accounts,
  );
  assert.equal(session?.email, EMAIL);
});

test("a wrong password is refused", async () => {
  const accounts = await configured();
  assert.equal(
    await verifyPressDemoAccount({ email: EMAIL, password: "not-the-password" }, accounts),
    null,
  );
  // Including the near miss: one character off is still off.
  assert.equal(
    await verifyPressDemoAccount({ email: EMAIL, password: `${PASSWORD} ` }, accounts),
    null,
  );
});

test("an unknown address is refused", async () => {
  const accounts = await configured();
  assert.equal(
    await verifyPressDemoAccount({ email: "someone@else.example", password: PASSWORD }, accounts),
    null,
  );
});

test("an empty password is refused, whatever is configured", async () => {
  const accounts = await configured();
  assert.equal(await verifyPressDemoAccount({ email: EMAIL, password: "" }, accounts), null);
  assert.equal(await verifyPressDemoAccount({ email: EMAIL }, accounts), null);
  assert.equal(await verifyPressDemoAccount({}, accounts), null);
  assert.equal(await verifyPressDemoAccount(undefined, accounts), null);
});

// The one that matters. A build nobody provisioned must be a build nobody can
// enter, not one that falls back to something convenient.
test("with no account configured, nobody signs in", async () => {
  assert.deepEqual(PRESS_DEMO_ACCOUNTS, [], "this suite is the unconfigured build");
  assert.equal(PRESS_DEMO_GATE_ACTIVE, false);
  assert.equal(PRESS_SIGN_IN_AVAILABLE, false, "no form may be offered with nothing behind it");
  for (const password of ["", "anything", PASSWORD]) {
    assert.equal(await verifyPressDemoAccount({ email: EMAIL, password }), null);
    assert.equal(await verifyPressDemoAccount({ email: EMAIL, password }, []), null);
  }
});

test("configuration that is not an account list yields no accounts", () => {
  for (const raw of ["", "   ", null, undefined, "not json", "[]", '["a"]', "42", '"a"', "null"]) {
    assert.deepEqual(parsePressDemoAccounts(raw), [], `rejected: ${String(raw)}`);
  }
});

test("a record that is not unmistakably a hash is dropped", () => {
  const cases = {
    "no salt": { hash: "a".repeat(64), tier: "press" },
    "no hash": { salt: SALT, tier: "press" },
    // The failure this check exists for: a password pasted where the digest
    // goes. Accepting it would put the plaintext in the bundle, which is the
    // one thing this whole module is arranged to prevent.
    "a plaintext password": { salt: SALT, hash: "hunter2", tier: "press" },
    "a short digest": { salt: SALT, hash: "abc123", tier: "press" },
    "a non-hex digest": { salt: SALT, hash: "z".repeat(64), tier: "press" },
    "an unsold tier": { salt: SALT, hash: "a".repeat(64), tier: "grove" },
    "an invented tier": { salt: SALT, hash: "a".repeat(64), tier: "admin" },
  };
  for (const [why, record] of Object.entries(cases)) {
    assert.deepEqual(parsePressDemoAccounts(JSON.stringify({ [EMAIL]: record })), [], why);
  }
});

test("one bad record does not lock out a good one", async () => {
  const good = await hashPressDemoPassword(SALT, PASSWORD);
  const accounts = parsePressDemoAccounts(
    JSON.stringify({
      "broken@example.org": { salt: SALT, hash: "nope" },
      [EMAIL]: { salt: SALT, hash: good, tier: "press" },
    }),
  );
  assert.equal(accounts.length, 1);
  assert.equal(accounts[0].email, EMAIL);
  assert.equal(accounts[0].workspace_tier, "press");
});

test("a record with no tier is the cheaper shelf, never the deeper one", () => {
  const accounts = parsePressDemoAccounts(
    JSON.stringify({ [EMAIL]: { salt: SALT, hash: "a".repeat(64) } }),
  );
  assert.equal(accounts[0]?.workspace_tier, "press");
});

test("a hash is accepted whatever case it was pasted in", async () => {
  const digest = await hashPressDemoPassword(SALT, PASSWORD);
  const accounts = parsePressDemoAccounts(
    JSON.stringify({ [EMAIL]: { salt: SALT, hash: digest.toUpperCase(), tier: "press" } }),
  );
  assert.equal(accounts.length, 1);
  assert.ok(await verifyPressDemoAccount({ email: EMAIL, password: PASSWORD }, accounts));
});

// The copy is part of the contract, not decoration: a demo gate that lets a
// reader believe it is access control is the failure this module is written
// to avoid.
test("the notice says what the gate is and is not", () => {
  assert.match(PRESS_DEMO_UNCONFIGURED, /not available/i);
  assert.equal(PRESS_DEMO_ACCOUNTS_VAR, "VITE_PRESS_DEMO_ACCOUNTS");
});
