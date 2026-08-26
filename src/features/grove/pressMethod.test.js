// The method sections carry claims about the product and a policy that
// decides who gets a tribe's records, so the things that would be quietly
// wrong if a list were edited are pinned here rather than only proofread.

import assert from "node:assert/strict";
import test from "node:test";

import {
  CONSTRUCTION_STEPS,
  DISCOVERY_MOVES,
  ECOSYSTEM_COLLECTIONS,
  ECOSYSTEM_EXAMPLES,
  EXPERTISE_DOMAINS,
  EXPERTISE_STRIP,
  MAINTENANCE_TIMELINE,
  MAINTENANCE_TRACKED,
  REPLICATION_CALLOUTS,
  SOURCE_KINDS,
  TRIBAL_REQUEST,
} from "./pressMethod.js";

const ALL_STRINGS = [
  ...EXPERTISE_DOMAINS,
  ...EXPERTISE_STRIP.map((d) => d.label),
  ...SOURCE_KINDS,
  ...CONSTRUCTION_STEPS.flatMap((s) => [s.label, s.note]),
  ...DISCOVERY_MOVES,
  ...MAINTENANCE_TRACKED,
  ...MAINTENANCE_TIMELINE.map((e) => e.event),
  ...ECOSYSTEM_COLLECTIONS.map((c) => c.label),
  ...ECOSYSTEM_EXAMPLES,
  ...REPLICATION_CALLOUTS,
  TRIBAL_REQUEST.policy,
  ...TRIBAL_REQUEST.eligibility,
  ...TRIBAL_REQUEST.verification,
  ...TRIBAL_REQUEST.included,
  ...TRIBAL_REQUEST.excluded,
  ...TRIBAL_REQUEST.purposes,
];

// The brand lock in CLAUDE.md, applied to displayed copy.
test("no em dashes anywhere in the method copy", () => {
  for (const line of ALL_STRINGS) {
    assert.ok(!line.includes("—"), line);
  }
});

test("no antithesis constructions in the method copy", () => {
  // "not X, it is Y" and "not X but Y" used as a rhetorical beat.
  const beats = [/\bis not\b[^.]*\.\s*(It|That)\s+is\b/i, /\bnot\b[^.,]{1,60},\s*(it'?s|it is)\b/i];
  for (const line of ALL_STRINGS) {
    for (const beat of beats) {
      assert.ok(!beat.test(line), line);
    }
  }
});

test("the pipeline starts at the public records and ends at maintenance", () => {
  assert.equal(CONSTRUCTION_STEPS[0].id, "fragmented");
  assert.equal(CONSTRUCTION_STEPS.at(-1).id, "maintained");
  assert.equal(new Set(CONSTRUCTION_STEPS.map((s) => s.id)).size, CONSTRUCTION_STEPS.length);
});

test("the timeline runs forward in time", () => {
  const years = MAINTENANCE_TIMELINE.map((entry) => Number(entry.year));
  assert.deepEqual(years, [...years].sort((a, b) => a - b));
  assert.ok(years.every(Number.isInteger));
});

// The strip is a summary of the domain list, so it must not claim expertise
// the list does not name, and it must not quietly drop a domain either.
test("every strip icon covers domains the long list actually names", () => {
  for (const domain of EXPERTISE_STRIP) {
    assert.ok(domain.covers.length > 0, domain.label);
    for (const covered of domain.covers) {
      assert.ok(EXPERTISE_DOMAINS.includes(covered), `${domain.label}: ${covered}`);
    }
  }
});

test("every domain is covered by one of the six strip icons", () => {
  const covered = new Set(EXPERTISE_STRIP.flatMap((domain) => domain.covers));
  for (const domain of EXPERTISE_DOMAINS) {
    assert.ok(covered.has(domain), domain);
  }
});

// The scope split is the part of the policy that stops one tribe's package
// from carrying another tribe's records, so it must not overlap.
test("the tribal request scope does not both include and exclude anything", () => {
  const included = new Set(TRIBAL_REQUEST.included.map((s) => s.toLowerCase()));
  for (const excluded of TRIBAL_REQUEST.excluded) {
    assert.ok(!included.has(excluded.toLowerCase()), excluded);
  }
});

test("the tribal request policy withholds other tribes and the entity graph", () => {
  const excluded = TRIBAL_REQUEST.excluded.join(" ").toLowerCase();
  assert.match(excluded, /other tribes/);
  assert.match(excluded, /entity graph/);
  assert.match(excluded, /crosswalk/);
});

// The whole point of the rewrite: claimed affiliation is not sufficient.
test("the policy requires the tribal government, not a claim of affiliation", () => {
  const policy = TRIBAL_REQUEST.policy.toLowerCase();
  assert.match(policy, /will not release/);
  assert.match(policy, /claims affiliation/);
  assert.match(policy, /federally recognized tribal government/);
  assert.match(policy, /independently verify/);
});

test("verification can reach the tribal government directly", () => {
  const verification = TRIBAL_REQUEST.verification.join(" ").toLowerCase();
  assert.match(verification, /official tribal government email/);
  assert.match(verification, /signed authorization letter/);
});

test("every ecosystem collection has a label and a unique id", () => {
  assert.equal(
    new Set(ECOSYSTEM_COLLECTIONS.map((c) => c.id)).size,
    ECOSYSTEM_COLLECTIONS.length,
  );
  assert.ok(ECOSYSTEM_COLLECTIONS.every((c) => c.label.trim().length > 0));
});
