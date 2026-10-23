import { expect, test as base } from "@playwright/test";

// The API allows ten sign-ins per client per window. The suite signs in far
// more often than that from one address, so each test presents its own.
// Needs CEDAR_PRESS_TRUST_PROXY=1 on the API (playwright.config.js).
export const test = base.extend({
  context: async ({ context }, provide, testInfo) => {
    const seq = (globalThis.__smokeSeq = (globalThis.__smokeSeq ?? 0) + 1);
    const ip = `10.${(testInfo.workerIndex % 250) + 1}.${(seq >> 8) & 255}.${seq & 255}`;
    await context.route("**/api/**", (route) =>
      route.continue({ headers: { ...route.request().headers(), "x-forwarded-for": ip } }),
    );
    await provide(context);
  },
});

export { expect };

/** The article service refusing, to reach the "Articles are unavailable" states that a connected API does not show. */
export function articlesDown(page) {
  return page.route("**/api/press/articles**", (route) => route.fulfill({ status: 503, body: "" }));
}

/** A current release feed with three collections, which the fixture API (no release builds) cannot serve. */
export function releasesFeed(page) {
  const releases = ["funding", "deals", "federal-register"].map((id, i) => {
    const version = String(i + 1).repeat(64).replace(/[^a-f0-9]/g, "a");
    return {
      id, version, updated: null, retired: false, record_count: 1000 + i,
      history: [{ version, date: null, date_basis: "not_recorded", kind: "data", changed: ["Collection updated."] }],
    };
  });
  return page.route("**/api/press/releases", (route) =>
    route.fulfill({ json: { source: "verified_current", history_complete: false, releases } }));
}
