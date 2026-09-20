// The line under a Cedar answer. The case worth a test file of its own is the
// locked collection: the server answers it with a description read off the
// release, and the panel used to put "View supporting records" underneath —
// one sentence after the answer had said those records open with Cedar
// Press+. Every assertion below exists because that contradiction shipped.

import assert from "node:assert/strict";
import test from "node:test";

import { answerSource, releaseOf } from "./cedarAnswer.js";

const basis = (over = {}) => ({
  kind: "release",
  collectionId: "need",
  collectionName: "Cedar Native Entity Enterprise Dataset (NEED)",
  version: "v1",
  updated: "2026-09-04",
  opened: true,
  ...over,
});

test("no basis means no line, rather than an empty one", () => {
  assert.equal(answerSource(null), null);
  assert.equal(answerSource(undefined), null);
  assert.equal(answerSource({}), null);
  assert.equal(answerSource({ collectionId: "need" }), null);
});

test("an included collection is cited to its release and offers its records", () => {
  const line = answerSource(basis());
  assert.equal(line.tone, "release");
  assert.equal(line.release, "Cedar Native Entity Enterprise Dataset (NEED) v1");
  assert.equal(line.updated, "2026-09-04");
  assert.equal(line.records, "need");
});

test("a collection this plan does not include is cited and offers nothing", () => {
  const line = answerSource(basis({ opened: false }));
  // Still read off the release, so it is still cited to it: the description
  // is a true reading and losing the citation would be the overcorrection.
  assert.equal(line.release, "Cedar Native Entity Enterprise Dataset (NEED) v1");
  assert.equal(line.updated, "2026-09-04");
  // The part that matters.
  assert.equal(line.tone, "description");
  assert.equal(line.records, null);
});

test("an omitted `opened` is not a grant", () => {
  // An older server that does not send the field must not be read as
  // permission. It costs a link, which is the cheap side of the mistake.
  const { opened, ...withoutField } = basis();
  assert.equal(opened, true);
  assert.equal(answerSource(withoutField).records, null);
  // And nothing truthy-but-not-true counts either.
  for (const value of [1, "true", "yes", {}]) {
    assert.equal(answerSource(basis({ opened: value })).records, null, String(value));
  }
});

test("nothing but a reachable release ever offers records", () => {
  // The invariant, stated once over every shape this can be handed.
  for (const kind of ["synthesis", "review", "release"]) {
    for (const opened of [true, false, undefined]) {
      const line = answerSource(basis({ kind, opened }));
      const reachable = kind === "release" && opened === true;
      assert.equal(line.records === null, !reachable, `${kind}/${opened}`);
    }
  }
});

test("a composed answer claims the scope and not the release", () => {
  const line = answerSource(basis({ kind: "synthesis" }));
  assert.equal(line.tone, "synthesis");
  assert.equal(line.records, null);
  // The scope is a real fact about the question, so the name survives; the
  // date does not, because nothing was read on that date.
  assert.equal(line.release, "Cedar Native Entity Enterprise Dataset (NEED) v1");
  assert.equal(line.updated, null);
});

test("a review is not an answer and cites nothing", () => {
  const line = answerSource(basis({ kind: "review" }));
  assert.equal(line.tone, "review");
  assert.equal(line.records, null);
  assert.equal(line.updated, null);
});

test("a release with no name or version reads as an empty string, not `undefined`", () => {
  // The panel prints this straight into a sentence; "Based on undefined" is
  // the failure mode a join with no filter produces.
  assert.equal(releaseOf({}), "");
  assert.equal(releaseOf({ collectionName: "Owned" }), "Owned");
  assert.equal(releaseOf({ version: "v1" }), "v1");
  assert.equal(answerSource({ kind: "synthesis" }).release, "");
});
