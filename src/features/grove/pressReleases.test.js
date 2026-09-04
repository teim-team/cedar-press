// The release record is derived from the manifest, so what these pin is the
// derivation: every storefront collection has a release, the release is the
// descriptor's, and nothing editorial can run ahead of what shipped.

import assert from "node:assert/strict";
import test from "node:test";

import { LAUNCH_COLLECTION } from "./collection.js";
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
// download filename carry.
test("the release is the descriptor's version and date", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const release = releaseFor(dataset.id);
    assert.equal(release.version, dataset.version, dataset.id);
    assert.equal(release.updated, dataset.updated, dataset.id);
    assert.equal(release.history.at(-1).version, dataset.version, dataset.id);
    assert.equal(release.history.at(-1).date, dataset.updated, dataset.id);
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

// Editorial notes describe shipped releases. A note dated after the
// descriptor's own date describes a release the manifest has not seen.
test("no editorial note runs ahead of the manifest", () => {
  for (const [id, notes] of Object.entries(RELEASE_NOTES)) {
    const dataset = LAUNCH_COLLECTION.find((item) => item.id === id);
    assert.ok(dataset, `${id} has notes and is not sold`);
    for (const note of notes) {
      assert.ok(note.date <= dataset.updated, `${id} ${note.version} is dated after the descriptor`);
      assert.ok(Object.values(RELEASE_KIND).includes(note.kind), `${id} ${note.version}`);
      assert.ok(note.changed?.length, `${id} ${note.version} changes nothing`);
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
