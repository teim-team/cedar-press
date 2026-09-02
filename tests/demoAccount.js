/**
 * The account the smoke suite signs in with.
 *
 * The standalone gate takes its account from `VITE_PRESS_DEMO_ACCOUNTS` at
 * build time and, given none, signs nobody in — which is the whole point of
 * it, and which means a browser suite that signs in has to provision one.
 * This is that provisioning: `playwright.config.js` puts `ACCOUNTS_JSON` into
 * the environment of the build it starts, and `smoke.spec.js` types `EMAIL`
 * and `PASSWORD` into the form.
 *
 * THE PASSWORD IS IN THIS FILE, ON PURPOSE, AND IT IS NOT A CREDENTIAL.
 * It provisions nothing. No deployment is configured with this account: the
 * Pages build reads its own value from repository configuration, and this one
 * exists for the length of a `npm run test:smoke` and nowhere else. A test
 * that types a password has to know it, and the alternative — reading a real
 * one from the environment — would make the suite pass or fail depending on
 * whose machine it ran on.
 *
 * The digest is derived here rather than pasted, by the same function the
 * browser verifies with, so the fixture cannot drift out of agreement with
 * the module it is testing.
 */
import { hashPressDemoPassword } from "../src/features/grove/pressDemoGate.js";

/** Unmistakably a fixture: `.invalid` can never be a real address (RFC 2606). */
export const EMAIL = "smoke@cedar-press.invalid";
export const PASSWORD = "smoke-fixture-not-a-credential";

const SALT = "smoke-fixture-salt";

/** Cedar Press+, so the suite exercises the whole shelf a reviewer sees. */
export const TIER = "press_pro";

/** Exported so a test can assert this is what the bundle carries, not PASSWORD. */
export const HASH = await hashPressDemoPassword(SALT, PASSWORD);

export const ACCOUNTS_JSON = JSON.stringify({
  [EMAIL]: { salt: SALT, hash: HASH, tier: TIER },
});
