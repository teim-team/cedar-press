import assert from "node:assert/strict";
import test from "node:test";

import { domainClass, domainOf, profileSegments } from "./subscriberProfile.js";

test("tribal government domains are recognized in the forms tribes actually use", () => {
  assert.equal(domainClass("chairman@navajo-nsn.gov"), "tribal_government");
  assert.equal(domainClass("a@srpmic-nsn.gov"), "tribal_government");
  assert.equal(domainClass("a@example.nsn.us"), "tribal_government");
});

test("a tribal domain is not collapsed into federal because it ends in .gov", () => {
  assert.notEqual(domainClass("a@navajo-nsn.gov"), "federal");
});

test("federal and academic domains are distinguished", () => {
  assert.equal(domainClass("officer@bia.gov"), "federal");
  assert.equal(domainClass("a@treasury.gov"), "federal");
  assert.equal(domainClass("a@base.mil"), "federal");
  assert.equal(domainClass("prof@asu.edu"), "academic");
});

test("a commercial domain classifies as other rather than guessing", () => {
  assert.equal(domainClass("ceo@enterprise.com"), "other");
  assert.equal(domainClass(""), "other");
  assert.equal(domainClass(undefined), "other");
});

test("a domain that merely contains gov is not treated as government", () => {
  assert.equal(domainClass("a@governance-partners.com"), "other");
  assert.equal(domainClass("a@nsn.gov.example.com"), "other");
});

test("domainOf takes the last @, so a quoted local part cannot spoof it", () => {
  assert.equal(domainOf('"weird@name"@bia.gov'), "bia.gov");
  assert.equal(domainOf("no-at-sign"), "");
});

test("segments carry the class of a subscriber, never the subscriber", () => {
  const segments = profileSegments({
    email: "chairman@navajo-nsn.gov",
    workspace_tier: "press",
  });
  assert.deepEqual(segments, { tier: "press", organizationClass: "tribal_government" });
  const serialized = JSON.stringify(segments);
  assert.ok(!serialized.includes("navajo-nsn.gov"), "no domain");
  assert.ok(!serialized.includes("chairman"), "no address");
});

test("an unknown session still segments", () => {
  assert.deepEqual(profileSegments(null), { tier: "unknown", organizationClass: "other" });
});
