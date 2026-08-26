import assert from "node:assert/strict";
import test from "node:test";

import {
  ORGANIZATION_KINDS,
  ROLES,
  domainOf,
  isProfileComplete,
  likelyOrganizationKind,
  normalizeProfile,
  organizationLabel,
  profileSegments,
} from "./subscriberProfile.js";

test("a tribal government domain is recognized in the forms tribes actually use", () => {
  assert.equal(likelyOrganizationKind("chairman@navajo-nsn.gov"), "tribal_government");
  assert.equal(likelyOrganizationKind("a@srpmic-nsn.gov"), "tribal_government");
  assert.equal(likelyOrganizationKind("a@example.nsn.us"), "tribal_government");
});

test("federal and academic domains are distinguished from tribal ones", () => {
  assert.equal(likelyOrganizationKind("officer@bia.gov"), "federal");
  assert.equal(likelyOrganizationKind("a@treasury.gov"), "federal");
  assert.equal(likelyOrganizationKind("a@state.mil"), "federal");
  assert.equal(likelyOrganizationKind("prof@asu.edu"), "academic");
});

test("a commercial domain says nothing, so the question is still asked", () => {
  assert.equal(likelyOrganizationKind("ceo@enterprise.com"), null);
  assert.equal(likelyOrganizationKind(""), null);
  assert.equal(likelyOrganizationKind(undefined), null);
});

test("a domain that merely contains gov is not treated as government", () => {
  assert.equal(likelyOrganizationKind("a@governance-partners.com"), null);
  assert.equal(likelyOrganizationKind("a@nsn.gov.example.com"), null);
});

test("domainOf takes the last @, so a quoted local part cannot spoof it", () => {
  assert.equal(domainOf('"weird@name"@bia.gov'), "bia.gov");
  assert.equal(domainOf("no-at-sign"), "");
});

test("normalize drops values the taxonomy does not know", () => {
  const profile = normalizeProfile({
    organizationKind: "not_a_kind",
    role: "Supreme Overlord",
    organization: "  Example Nation  ",
  });
  assert.equal(profile.organizationKind, null);
  assert.equal(profile.role, null);
  assert.equal(profile.organization, "Example Nation");
});

test("normalize keeps values the taxonomy does know", () => {
  const profile = normalizeProfile({
    organizationKind: ORGANIZATION_KINDS[0].id,
    role: ROLES[0],
    organization: "x".repeat(200),
  });
  assert.equal(profile.organizationKind, ORGANIZATION_KINDS[0].id);
  assert.equal(profile.role, ROLES[0]);
  assert.equal(profile.organization.length, 120, "a long name is capped, not rejected");
});

test("a profile is complete only with both answers", () => {
  assert.equal(isProfileComplete(null), false);
  assert.equal(isProfileComplete({ organizationKind: "federal" }), false);
  assert.equal(isProfileComplete({ role: ROLES[0] }), false);
  assert.equal(isProfileComplete({ organizationKind: "federal", role: ROLES[0] }), true);
});

test("segments carry the class of a subscriber, never the subscriber", () => {
  const segments = profileSegments(
    { email: "chairman@navajo-nsn.gov", workspace_tier: "press" },
    { organizationKind: "tribal_government", role: ROLES[0], organization: "Example Nation" },
  );
  assert.equal(segments.tier, "press");
  assert.equal(segments.organizationKind, "tribal_government");
  assert.equal(segments.domainClass, "tribal_government");
  const serialized = JSON.stringify(segments);
  assert.ok(!serialized.includes("navajo-nsn.gov"), "no domain");
  assert.ok(!serialized.includes("chairman@"), "no address");
  assert.ok(!serialized.includes("Example Nation"), "no organization name");
});

test("an unanswered profile still segments, as unstated", () => {
  const segments = profileSegments({ email: "a@example.com", workspace_tier: "press_pro" }, null);
  assert.equal(segments.organizationKind, "unstated");
  assert.equal(segments.role, "unstated");
  assert.equal(segments.domainClass, "other");
});

test("an unknown organization id reads as unstated rather than throwing", () => {
  assert.equal(organizationLabel("retired_kind"), "Unstated");
  assert.equal(organizationLabel("federal"), "Federal agency");
});
