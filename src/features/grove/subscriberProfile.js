/**
 * PURPOSE
 * What the service can tell about a reader without asking them anything.
 *
 * Accounts arrive from a Tribal Business News subscription, so the service is
 * handed an address and nothing else — and a reader should not have to fill
 * in a form to use something they already pay for. The address itself
 * classifies most of the audience that matters: tribal governments sit on
 * `*.nsn.gov` and `*-nsn.gov`, federal staff on `*.gov` and `*.mil`,
 * researchers on `*.edu`. That is derived at sign-in, costs the reader
 * nothing, and is enough to answer the question the roadmap actually asks —
 * which kinds of organization are opening which collections.
 *
 * WHAT THIS IS NOT
 * It is not a person's job title, and it does not pretend to be: a
 * commercial domain classifies as `other`, because a tribal enterprise, a
 * lender and a consultant are indistinguishable from `@example.com`. Closing
 * that gap by sending addresses to an enrichment broker is a server-side
 * decision with legal and data-sovereignty consequences, not something a
 * browser does quietly to a reader — see docs/SUBSCRIBERS.md.
 */

/** The classes an address can place a reader in. */
export const DOMAIN_CLASSES = Object.freeze([
  "tribal_government",
  "federal",
  "academic",
  "other",
]);

/** The domain half of an address, lowercased. */
export function domainOf(email) {
  const at = String(email ?? "").lastIndexOf("@");
  return at === -1 ? "" : String(email).slice(at + 1).trim().toLowerCase();
}

/**
 * The organization class an address implies, or "other" when it implies
 * nothing. Tribal governments are the case worth getting right: most sit on
 * `*.nsn.gov`, `*.nsn.us` or `*-nsn.gov`, which no generic classifier knows,
 * and collapsing them into "federal" because the suffix says `.gov` would
 * erase exactly the distinction this service exists to make.
 */
export function domainClass(email) {
  const domain = domainOf(email);
  if (!domain) return "other";
  if (/(^|\.)nsn\.(gov|us)$/.test(domain) || /-nsn\.(gov|us)$/.test(domain)) {
    return "tribal_government";
  }
  if (/(^|\.)mil$/.test(domain)) return "federal";
  if (/(^|\.)gov$/.test(domain)) return "federal";
  if (/(^|\.)edu$/.test(domain)) return "academic";
  return "other";
}

/**
 * What telemetry may carry about a subscriber: the segments a dashboard
 * groups by, and nothing that identifies the person. The class of the
 * domain, never the domain — "federal", not "bia.gov" — because a single
 * tribe's domain in an analytics tool identifies the reader on its own.
 */
export function profileSegments(user) {
  return {
    tier: user?.workspace_tier ?? "unknown",
    organizationClass: domainClass(user?.email),
  };
}
