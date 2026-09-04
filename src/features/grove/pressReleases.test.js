// The release record is derived from the manifest, so what these pin is the
// derivation: every storefront collection has a release, the release is the
// descriptor's, and nothing editorial can run ahead of what shipped.

import assert from "node:assert/strict";
import test from "node:test";

import { readFileSync } from "node:fs";

import {
  EXCLUDED_COLLECTIONS,
  LAUNCH_COLLECTION,
  collectionCedarFacts,
  collectionSample,
} from "./collection.js";
import { PRESS_CATALOG } from "./pressCatalog.js";
import {
  CADENCE,
  DECLARED_CADENCE,
  PRESS_RELEASES,
  RELEASE_FEED,
  RELEASE_KIND,
  RELEASE_NOTES,
  anchorOf,
  formatUpdated,
  freshnessLine,
  latestRelease,
  ledgerFor,
  recentActivity,
  recentlyUpdated,
  releaseFor,
} from "./pressReleases.js";

// The feed used to cover ten collections while the storefront sold twelve,
// and one of the ten was not sold at all.
test("every storefront collection has a release and nothing else does", () => {
  assert.deepEqual(
    Object.keys(PRESS_RELEASES).sort(),
    LAUNCH_COLLECTION.map((dataset) => dataset.id).sort(),
  );
  for (const entry of PRESS_CATALOG) {
    assert.ok(releaseFor(entry.id), `${entry.id} has no release`);
  }
});

// A reader citing a version from the feed must download that version: the
// feed's version is the descriptor's, which is the one the citation and the
// download filename carry, and the ledger holds that version at the head of
// the history with the descriptor's own date.
test("the release is the descriptor's version and date, and the ledger holds it", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const release = releaseFor(dataset.id);
    assert.equal(release.version, dataset.version, dataset.id);
    assert.equal(release.updated, dataset.updated, dataset.id);
    assert.equal(
      release.history[0].version,
      dataset.version,
      `${dataset.id}: the manifest is at ${dataset.version} and the ledger is not; run node scripts/record-release.mjs`,
    );
    assert.equal(release.history[0].date, dataset.updated, dataset.id);
  }
});

// The ledger is append-only and a recorded version keeps the facts it was
// recorded with. The entry for the CURRENT version must equal what the
// manifest measures now: a descriptor re-imported with different facts under
// the same version is a version that should have been bumped, and the ledger
// must not be quietly rewritten to agree with it.
test("the ledger's entry for the current version is what the manifest measures", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const record = ledgerFor(dataset.id).find((item) => item.version === dataset.version);
    assert.ok(record, `${dataset.id} ${dataset.version} is not in the ledger`);
    const cedar = collectionCedarFacts(dataset.id);
    const sample = collectionSample(dataset.id);
    assert.deepEqual(record, {
      version: dataset.version,
      date: dataset.updated,
      tables: cedar.n_tables,
      rowsLabel: dataset.rowsLabel,
      preview: sample?.path ? { table: sample.table, rows: sample.rows, of: sample.of } : null,
      // By name, not by count: a blocker that changed is a fact that changed.
      blockers: [...cedar.blockers],
    }, `${dataset.id} ${dataset.version}: the ledger and the manifest disagree`);
  }
});

// The ledger is append-only, so a collection the storefront retires keeps its
// releases here: a citation of its v0 still resolves. What the ledger may not
// hold is a collection the workspace has never measured at all. Every id must
// be one the manifest ships or one it lists as excluded (Codex, PR #52).
test("every version in the ledger is unique, dated and no newer than the descriptor", () => {
  const known = new Set([
    ...LAUNCH_COLLECTION.map((dataset) => dataset.id),
    ...EXCLUDED_COLLECTIONS.map((entry) => entry.id),
  ]);
  const ledger = JSON.parse(readFileSync(new URL("../../../data/cedar/releases.json", import.meta.url), "utf8"));
  for (const [id, records] of Object.entries(ledger.releases)) {
    assert.ok(known.has(id), `${id} is in the ledger and the workspace has never measured it`);
    const versions = records.map((record) => record.version);
    assert.equal(new Set(versions).size, versions.length, `${id} records a version twice`);
    const dates = records.map((record) => record.date);
    assert.deepEqual(dates, [...dates].sort(), `${id}: the ledger is not in date order`);
    const dataset = LAUNCH_COLLECTION.find((item) => item.id === id);
    for (const record of records) {
      assert.match(record.date, /^\d{4}-\d{2}-\d{2}$/, `${id} ${record.version}`);
      assert.ok(Array.isArray(record.blockers), `${id} ${record.version} records blockers by count, not by name`);
      if (dataset) {
        assert.ok(record.date <= dataset.updated, `${id} ${record.version} is dated after the descriptor`);
      }
    }
    // A retired collection has no release record on the storefront.
    if (!dataset) assert.equal(releaseFor(id), null, `${id} is retired and still has a release`);
  }
});

// Only the current release's preview is a file on the shelf.
test("only the current release says its preview downloads", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const [current, ...older] = releaseFor(dataset.id).history;
    if (collectionSample(dataset.id)?.path) {
      assert.ok(current.changed.some((line) => line.endsWith("downloads from the shelf.")), dataset.id);
    }
    for (const entry of older) {
      assert.ok(!entry.changed.some((line) => line.includes("downloads from the shelf")), `${dataset.id} ${entry.version}`);
    }
  }
});

test("every collection declares a cadence, and it is one of the known ones", () => {
  const known = new Set(Object.values(CADENCE));
  for (const dataset of LAUNCH_COLLECTION) {
    assert.ok(DECLARED_CADENCE[dataset.id], `${dataset.id} declares no cadence`);
    assert.ok(known.has(DECLARED_CADENCE[dataset.id]), dataset.id);
    assert.equal(releaseFor(dataset.id).cadence, DECLARED_CADENCE[dataset.id]);
  }
  for (const id of Object.keys(DECLARED_CADENCE)) {
    assert.ok(releaseFor(id), `${id} declares a cadence and is not sold`);
  }
});

// The first release's notes are what the manifest measures, said plainly.
// No note may carry a number the manifest does not: the table count and the
// row label are copied, never typed.
test("the first release says what the manifest measures", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const first = releaseFor(dataset.id).history.at(-1);
    assert.equal(first.kind, RELEASE_KIND.DATA);
    assert.ok(first.changed.length >= 2, dataset.id);
    assert.match(first.changed[0], /^First release on Cedar Press: /);
    assert.ok(first.changed[0].includes(dataset.rowsLabel), `${dataset.id}: ${first.changed[0]}`);
  }
  // The one collection with no preview file says so rather than promising one.
  const owned = releaseFor("owned").history.at(-1);
  assert.ok(owned.changed.some((line) => line.startsWith("No preview file yet")));
  const funding = releaseFor("funding").history.at(-1);
  assert.ok(funding.changed.some((line) => /-row preview of /.test(line)));
});

// Editorial notes describe shipped releases: a note names a version the
// ledger holds, and nothing else.
test("every editorial note overlays a version the ledger holds", () => {
  for (const [id, notes] of Object.entries(RELEASE_NOTES)) {
    const versions = new Set(ledgerFor(id).map((record) => record.version));
    assert.ok(versions.size, `${id} has notes and no ledger`);
    for (const [version, note] of Object.entries(notes)) {
      assert.ok(versions.has(version), `${id} ${version} is noted and never shipped`);
      assert.ok(Object.values(RELEASE_KIND).includes(note.kind), `${id} ${version}`);
      assert.ok(note.changed?.length, `${id} ${version} changes nothing`);
      const rendered = releaseFor(id).history.find((entry) => entry.version === version);
      assert.deepEqual([...rendered.changed], [...note.changed], `${id} ${version}: the note is not what renders`);
    }
  }
});

test("the feed is newest first, indexed and uniquely anchored", () => {
  const dates = RELEASE_FEED.map((entry) => entry.date);
  assert.deepEqual(dates, [...dates].sort().reverse());
  const anchors = RELEASE_FEED.map((entry) => entry.anchor);
  assert.equal(new Set(anchors).size, anchors.length);
  for (const entry of RELEASE_FEED) {
    assert.equal(entry.anchor, anchorOf(entry));
    assert.match(entry.anchor, /^[a-z0-9-]+$/, entry.anchor);
    assert.ok(entry.name && entry.name !== entry.id, entry.id);
    assert.equal(entry.haystack, entry.haystack.toLowerCase());
    assert.ok(entry.haystack.includes(entry.name.toLowerCase()));
  }
  assert.equal(RELEASE_FEED.length, Object.values(PRESS_RELEASES).reduce((n, r) => n + r.history.length, 0));
});

test("the activity summary counts the feed and nothing else", () => {
  const newest = RELEASE_FEED[0].date;
  const day = 86400000;
  const dayAfter = new Date(new Date(newest).getTime() + day);
  const inWindow = RELEASE_FEED.filter((e) => new Date(e.date).getTime() >= dayAfter.getTime() - 30 * day);
  const recent = recentActivity(30, dayAfter);
  assert.equal(recent.releases, inWindow.length);
  assert.equal(recent.collections, new Set(inWindow.map((e) => e.id)).size);
  assert.equal(recent.methodology, inWindow.filter((e) => e.kind === RELEASE_KIND.METHOD).length);
  assert.equal(recent.latest, newest);
  // Long after the last release the window is empty and the latest date stands.
  const later = recentActivity(30, new Date(new Date(newest).getTime() + 400 * day));
  assert.equal(later.releases, 0);
  assert.equal(later.latest, newest);
});

test("recently updated is deterministic when releases share a day", () => {
  const first = recentlyUpdated(3).map((r) => r.id);
  const again = recentlyUpdated(3).map((r) => r.id);
  assert.deepEqual(first, again);
  assert.equal(first.length, 3);
  assert.equal(recentlyUpdated(1)[0].id, RELEASE_FEED[0].id);
});

test("dates are spelled one way everywhere", () => {
  assert.equal(formatUpdated("2026-09-02"), "Sept. 2, 2026");
  assert.equal(formatUpdated(""), "");
  assert.match(freshnessLine("funding"), /^Updated Sept\. 2 · monthly$/);
  assert.equal(freshnessLine("not-a-collection"), "");
  assert.equal(latestRelease("nest").version, releaseFor("nest").version);
  assert.equal(latestRelease("not-a-collection"), null);
});
