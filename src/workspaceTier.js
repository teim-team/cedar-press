/**
 * REVIEW OWNER: Brian
 *
 * Tier resolution and tier copy shared across the app.
 *
 * Division of labour on this branch: Brian reviews login, signup and
 * anything that decides account identity, hierarchy or entitlement.
 * Kaylyn reviews product behaviour and UI. See docs/review/REVIEWERS.md.
 */

/**
 * Workspace tier helper.
 *
 * `workspaceTier` arrives on the session payload (set by
 * server/repositories/users.js and returned from /me), and
 * `resolveTier` reads it directly. Unknown or missing values fall
 * back to "sprout" to match the server's rule in
 * server/lib/tierCapabilities.js (pre-signup rows are provisioned
 * pilot accounts; self-serve signup sets "free" explicitly).
 */

/** @typedef {"free" | "sprout" | "sapling" | "tree" | "grove" | "press" | "press_pro"} WorkspaceTier */

export const WORKSPACE_TIERS = Object.freeze({
  // Seed is the DISPLAY name of the free account (founder decision,
  // 2026-08-25): the botanical ladder now starts at its beginning, Seed,
  // Sprout, Sapling, Tree. The machine identity stays `free` everywhere: the
  // database CHECK constraint, tierCapabilities, the signup handoff and
  // analytics all speak `free`, and renaming a stored value buys nothing.
  // Canonical one-liner, shared with lumecon.ai's protected vocabulary:
  // "Seed, the free account: build a full analysis and see your direct
  // effects; full results unlock on any plan."
  free: Object.freeze({
    id: "free",
    name: "Seed",
    userLimitLabel: "1 user",
    maxUsers: 1,
    accessLabel: "See your direct effects; full results unlock on any plan",
    features: Object.freeze([
      "1 user",
      "Bring your documents and build a full analysis end to end",
      "Cedar-assisted intake",
      "See your direct effects on the real results page",
      "Full results unlock on any plan",
    ]),
    setupFeatures: Object.freeze([]),
  }),
  sprout: Object.freeze({
    id: "sprout",
    name: "Sprout",
    userLimitLabel: "1 user",
    maxUsers: 1,
    accessLabel: "Full platform access",
    features: Object.freeze([
      "1 user",
      "The full Lumecon model, unlimited analysis",
      "Cedar-assisted intake and PDF/source import",
      "Every supported U.S. geography, county to nation",
      "Past, future and multi-year analyses",
      "Shareable PDF and CSV exports",
      "Full assumption ledger on every export",
      "Standard email support",
    ]),
    setupFeatures: Object.freeze([
      "Cedar Commons (shared projects, review workflows)",
      "Up to 10 collaborators in one organization",
    ]),
  }),
  sapling: Object.freeze({
    id: "sapling",
    name: "Sapling",
    userLimitLabel: "Up to 10 users",
    maxUsers: 10,
    accessLabel: "Full platform access",
    features: Object.freeze([
      "Everything in Sprout",
      "Up to 10 users",
      "Cedar Commons: shared projects, collaborative analysis and review workflows",
      "Priority setup",
    ]),
    setupFeatures: Object.freeze([
      "Cedar Grove (organizational data library)",
      "Hands-on Cedar calibration",
      "Unlimited users in one organization",
    ]),
  }),
  // Cedar Press, in two rungs. Both are sold only through an eligible Tribal
  // Business News membership: the membership issues an access code, the code
  // creates the account. Standalone, and not included with Grove or Tree.
  //
  // Standard carries part of the collection. The rest is visible but capped,
  // with the upgrade in the place the data would be, so a reader can see what
  // they do not have rather than not knowing it exists.
  //
  // No prices here on purpose. Prices belong to the marketing site and to
  // whatever the working session settles; entitlement code that carries a
  // number goes stale the first time one changes.
  press: Object.freeze({
    id: "press",
    name: "Cedar Press",
    userLimitLabel: "1 reader",
    maxUsers: 1,
    accessLabel: "Cedar Press, with part of the collection",
    features: Object.freeze([
      "The Data Briefs and the collection's figures",
      "The collections on the Cedar Press shelf, with their methods and versions",
      "The citation register",
      "Available only through a Tribal Business News access code",
    ]),
    setupFeatures: Object.freeze([
      "The rest of the Cedar Press collection (Cedar Press+)",
      "Every dataset including the Grove-only ones, with bulk export (Cedar Grove)",
    ]),
  }),
  press_pro: Object.freeze({
    id: "press_pro",
    name: "Cedar Press+",
    userLimitLabel: "1 reader",
    maxUsers: 1,
    accessLabel: "Cedar Press, with the whole Press collection",
    features: Object.freeze([
      "Everything in Cedar Press",
      "Six more collections: contracting, subcontracting, resource revenues, individually owned Native businesses, enterprise structures and nonprofits",
      "Versioned releases with documented methods",
    ]),
    setupFeatures: Object.freeze([
      "The datasets only Cedar Grove carries, with bulk export and benchmarks (Cedar Grove)",
      "Cedar, grounded in the collection (Cedar Grove)",
    ]),
  }),
  // The standalone Cedar Grove license. A product flag rather than a ladder
  // rung: the curated collection, Cedar and unlimited users, with the
  // modeling platform browsable the way the free trial is and full results
  // unlocking on upgrade.
  //
  // Grove is not Cedar Press and does not include it. They overlap in the
  // collection, not in access: Grove carries every dataset, including ones
  // Cedar Press does not, while Cedar Press carries most of them alongside
  // the journalism and the citation register, and is sold through Tribal
  // Business News.
  grove: Object.freeze({
    id: "grove",
    name: "Cedar Grove",
    userLimitLabel: "Unlimited users in one organization",
    maxUsers: null,
    accessLabel: "The curated collection; platform results unlock on upgrade",
    features: Object.freeze([
      "Every dataset in the collection, including the ones Cedar Press does not carry",
      "Bulk export and benchmarks across every collection at once",
      "The public data reporting and compliance routinely need: Census, BLS, BEA and more",
      "New economic development datasets as they release",
      "Cedar, grounded in the collection",
      "Learns your organization's workflows the longer you use it",
      "Documented methods and versioned releases",
      "Unlimited users in one organization",
      "Build platform analyses end to end; full results unlock on upgrade",
    ]),
    setupFeatures: Object.freeze([
      "Organizational insights and your own data (comes with Tree)",
      "The full Lumecon model and study workflow (comes with Tree)",
    ]),
  }),
  tree: Object.freeze({
    id: "tree",
    name: "Tree",
    userLimitLabel: "Unlimited users in one organization",
    // null = genuinely unlimited within one organization; never a hidden cap.
    maxUsers: null,
    accessLabel: "Full platform access",
    features: Object.freeze([
      "Everything in Sapling",
      "Unlimited users in one organization",
      "Cedar Grove: the clean, harmonized data library, augmentable with your own data",
      "Hands-on Cedar calibration",
      "Dedicated launch support",
    ]),
    setupFeatures: Object.freeze([]),
  }),
});

/**
 * Derives the workspace tier from whatever user/session data is available.
 * Falls back to "sprout" when tier info is absent.
 *
 * @param {object | null | undefined} user - The current auth user object.
 * @returns {WorkspaceTier}
 */
export function resolveTier(user) {
  const raw = user?.workspace_tier ?? user?.workspaceTier ?? null;
  if (
    raw === "free" ||
    raw === "sapling" ||
    raw === "tree" ||
    raw === "grove" ||
    raw === "press" ||
    raw === "press_pro"
  ) {
    return raw;
  }
  return "sprout";
}

export function getWorkspaceTierCopy(user) {
  return WORKSPACE_TIERS[resolveTier(user)];
}
