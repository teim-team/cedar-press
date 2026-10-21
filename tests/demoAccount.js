/**
 * The accounts the smoke suite signs in with.
 *
 * `playwright.config.js` hands `ACCOUNTS_JSON` to the API it starts as
 * `CEDAR_PRESS_ACCOUNTS`, and `smoke.spec.js` types `EMAIL` and `PASSWORD`
 * into the login page. Without a database the API compares the password in
 * plain text (server/cedar_press/subscribers.py), which is why it is here.
 *
 * THE PASSWORD IS IN THIS FILE, ON PURPOSE, AND IT IS NOT A CREDENTIAL.
 * No deployment is configured with these accounts: they exist for the length
 * of a `npm run test:smoke`, in an API on a port of its own, and nowhere else.
 * A test that types a password has to know it, and reading a real one from the
 * environment would make the suite pass or fail depending on whose machine it
 * ran on.
 */

/** Unmistakably a fixture: `.invalid` can never be a real address (RFC 2606). */
export const EMAIL = "smoke@cedar-press.invalid";
export const PRESS_EMAIL = "press-smoke@cedar-press.invalid";
export const PASSWORD = "smoke-fixture-not-a-credential";

/** Cedar Press+, so the suite exercises the whole shelf a reader sees. */
export const TIER = "press_pro";

export const ACCOUNTS_JSON = JSON.stringify({
  [EMAIL]: { password: PASSWORD, tier: TIER },
  [PRESS_EMAIL]: { password: PASSWORD, tier: "press" },
});

/** Fixed, because it signs nothing that outlives the run. */
export const SECRET = "smoke-fixture-secret-0123456789abcdef0123456789abcdef";
