/**
 * PURPOSE
 * Who the subscriber is, in the terms that decide what gets built next.
 *
 * Accounts arrive from a Tribal Business News subscription, which means the
 * service knows an email address and nothing else. A tribal chairman, a
 * lender's analyst and a reporter all read the same shelf today, and the
 * roadmap cannot tell them apart — so the request that matters most is
 * indistinguishable from the one that matters least.
 *
 * WHAT THIS COLLECTS, AND HOW
 * The subscriber says. Organization and role are asked once, in two
 * questions, and can be changed or skipped. The email's domain seeds a
 * likely answer (a `.gov` address is probably government) which the person
 * then confirms or corrects, so the guess is a shortcut rather than a
 * conclusion.
 *
 * WHAT THIS DOES NOT DO
 * It does not send the address to a third-party enrichment service to look
 * up an employer. That is a server-side decision with legal and
 * data-sovereignty consequences, not something a browser should do quietly
 * to a reader — least of all in a product whose argument is that Indian
 * Country's data deserves better handling than that. See
 * docs/SUBSCRIBERS.md.
 *
 * The role a person declares is also better data than a vendor's guess:
 * enrichment infers a title from a company record, while this is the reader
 * saying which seat they sit in.
 */

/** How a subscriber's organization relates to Indian Country's economy. */
export const ORGANIZATION_KINDS = Object.freeze([
  { id: "tribal_government", label: "Tribal government" },
  { id: "tribal_enterprise", label: "Tribal enterprise or corporation" },
  { id: "anc_nho", label: "ANC or NHO" },
  { id: "native_nonprofit", label: "Native nonprofit or association" },
  { id: "federal", label: "Federal agency" },
  { id: "state_local", label: "State or local government" },
  { id: "lender_investor", label: "Lender, investor or fund" },
  { id: "advisor", label: "Law, accounting or consulting firm" },
  { id: "media", label: "Newsroom or media" },
  { id: "academic", label: "University or research institute" },
  { id: "other", label: "Something else" },
]);

/**
 * The seat, not the title. Extends the platform's own role list
 * (pages/accountModel.js) with the seats a press subscription reaches that
 * the analysis product does not: reporters, lenders, federal staff.
 */
export const ROLES = Object.freeze([
  "Tribal Council Member or Elected Leader",
  "Tribal Administrator",
  "Tribal Treasurer or Finance Officer",
  "Economic Development Director",
  "Executive or General Manager",
  "Analyst",
  "Consultant",
  "Government Analyst or Program Officer",
  "Lender, Investor or Underwriter",
  "Reporter or Editor",
  "Researcher or Academic",
  "Other",
]);

const KIND_IDS = new Set(ORGANIZATION_KINDS.map((kind) => kind.id));

/** The domain half of an address, lowercased. */
export function domainOf(email) {
  const at = String(email ?? "").lastIndexOf("@");
  return at === -1 ? "" : String(email).slice(at + 1).trim().toLowerCase();
}

/**
 * A likely organization kind from the address alone, or null when the domain
 * says nothing. This seeds the question; it never answers it, because a
 * tribal enterprise on a commercial domain and a consultant on the same
 * domain look identical from here.
 *
 * Tribal governments are the case worth getting right: most sit on
 * `*.nsn.gov`, `*.nsn.us` or `*-nsn.gov`, which no generic classifier knows.
 */
export function likelyOrganizationKind(email) {
  const domain = domainOf(email);
  if (!domain) return null;
  if (/(^|\.)nsn\.(gov|us)$/.test(domain) || /-nsn\.(gov|us)$/.test(domain)) {
    return "tribal_government";
  }
  if (/(^|\.)bia\.gov$|(^|\.)ihs\.gov$/.test(domain)) return "federal";
  if (/(^|\.)mil$/.test(domain)) return "federal";
  if (/(^|\.)gov$/.test(domain)) return "federal";
  if (/(^|\.)edu$/.test(domain)) return "academic";
  return null;
}

/** Whether the profile has what the roadmap needs. */
export function isProfileComplete(profile) {
  return Boolean(profile?.organizationKind && profile?.role);
}

/** A stored profile, normalized: unknown values are dropped, not kept. */
export function normalizeProfile(raw) {
  if (!raw || typeof raw !== "object") return null;
  const organizationKind = KIND_IDS.has(raw.organizationKind) ? raw.organizationKind : null;
  const role = ROLES.includes(raw.role) ? raw.role : null;
  const organization = typeof raw.organization === "string" ? raw.organization.trim() : "";
  return {
    organizationKind,
    role,
    organization: organization.slice(0, 120),
    updatedAt: typeof raw.updatedAt === "string" ? raw.updatedAt : null,
    dismissed: Boolean(raw.dismissed),
  };
}

/**
 * What telemetry may carry about a subscriber: the segments a dashboard
 * groups by, and nothing that identifies the person. No address, no
 * organization name — a small newsroom's name in an analytics tool is
 * identifying on its own.
 */
export function profileSegments(user, profile) {
  return {
    tier: user?.workspace_tier ?? "unknown",
    organizationKind: profile?.organizationKind ?? "unstated",
    role: profile?.role ?? "unstated",
    // The domain's class, not the domain: "federal" rather than "bia.gov".
    domainClass: likelyOrganizationKind(user?.email) ?? "other",
  };
}

/**
 * The label for an organization kind, for the interface. Unknown ids read as
 * unstated rather than throwing: a kind retired on the server should not
 * break a page for someone whose profile still names it.
 */
export function organizationLabel(id) {
  return ORGANIZATION_KINDS.find((kind) => kind.id === id)?.label ?? "Unstated";
}
