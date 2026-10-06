import assert from "node:assert/strict";
import test from "node:test";

import {
  COLLECTION_FIGURES,
  LAUNCH_COLLECTION,
  collectionCedarFacts,
  collectionFindings,
  collectionSample,
  sampleUnavailableReason,
} from "./collection.js";

test("availability findings follow each current public preview and measured count", () => {
  const needs = collectionFindings().needs;
  assert.ok(!needs.some((need) => need.id === "col-need-owned-membership"));
  assert.ok(!needs.some((need) => need.id === "col-need-owned-terms"));
  for (const dataset of LAUNCH_COLLECTION) {
    const facts = collectionCedarFacts(dataset.id);
    const sample = collectionSample(dataset.id);
    const rowCountMissing = !Number.isSafeInteger(facts?.n_rows) || facts.n_rows < 0;
    const previewMissing = !sample?.path;
    const finding = needs.find((need) => need.id === `col-need-${dataset.id}-availability`);
    assert.equal(Boolean(finding), rowCountMissing || previewMissing, dataset.id);
    if (!finding) continue;
    assert.equal(finding.demonstration, false);
    assert.ok(finding.text.startsWith(dataset.name + ": "));
    assert.equal(finding.text.includes("does not state a row count"), rowCountMissing);
    if (previewMissing) {
      assert.ok(finding.text.includes(sampleUnavailableReason(dataset.id)
        || "No preview file is published for the current release."));
    }
  }
});

test("unmeasured vintages are named from the descriptors without guessing source coverage", () => {
  const missing = LAUNCH_COLLECTION.filter(
    (dataset) => typeof dataset.vintage !== "string" || !dataset.vintage.trim(),
  );
  const finding = collectionFindings().needs.find((need) => need.id === "col-need-vintage");
  assert.equal(Boolean(finding), missing.length > 0);
  if (!finding) return;
  assert.equal(finding.demonstration, false);
  assert.ok(finding.text.includes("An update date does not establish the periods covered by every source."));
  if (missing.length !== LAUNCH_COLLECTION.length) {
    for (const dataset of missing) assert.ok(finding.text.includes(dataset.name));
    assert.ok(!finding.text.startsWith("No collection"));
  }
});

test("prototype backlogs and lead readiness cannot read as live research results", () => {
  const { needs, narratives } = collectionFindings();
  for (const id of ["col-need-closing", "col-need-fy26", "col-need-matches"]) {
    const finding = needs.find((need) => need.id === id);
    assert.equal(finding.demonstration, true, id);
    assert.ok(finding.text.startsWith("Demonstration: "), id);
  }
  for (const lead of narratives) {
    assert.equal(lead.demonstration, true, lead.id);
    assert.ok(lead.name.startsWith("Demonstration: "), lead.id);
  }
});

test("the specifically dated White Earth roster remains a historical measured figure", () => {
  const figure = COLLECTION_FIGURES.find((item) => item.id === "owned");
  assert.equal(figure.demonstration, false);
  assert.equal(figure.basis, "White Earth Nation TERO roster, supplied 2026-08-28");
  assert.deepEqual(figure.points.map((point) => point.value), [17, 4, 1]);
});
