/**
 * Fixture accounts for the smoke suite. `playwright.config.js` passes
 * `ACCOUNTS_JSON` to the API it starts; the password is plain text because the
 * API compares it that way without a database. Not a credential: no
 * deployment is configured with it.
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
