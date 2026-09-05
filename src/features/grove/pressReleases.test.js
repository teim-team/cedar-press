// The release record is derived from the manifest, so what these pin is the
// derivation: every storefront collection has a release, the release is the
// descriptor's, and nothing editorial can run ahead of what shipped.

import assert from "node:assert/strict";
import test from "node:test";

import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  EXCLUDED_COLLECTIONS,
  LAUNCH_COLLECTION,
  collectionCedarFacts,
  collectionDeclaredSample,
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
  buildFeed,
  buildReleases,
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
    // The DECLARED sample: the ledger records what the release produced,
    // whether or not the repository holds the file today.
    const sample = collectionDeclaredSample(dataset.id);
    assert.deepEqual(record, {
      version: dataset.version,
      date: dataset.updated,
      name: dataset.name,
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
    // A retired collection keeps a read-only record: citable, not sold.
    if (!dataset) {
      assert.equal(releaseFor(id)?.retired, true, `${id} is retired and reads as sold`);
      assert.equal(releaseFor(id).cadence, null, id);
    }
  }
});

// The retired case, on a synthetic ledger since the real one has none: the
// permalink a citation names keeps resolving, the entry says it is history,
// and the overview's "recently updated" rail never carries it.
test("a retired collection stays in the feed as read-only history", () => {
  const first = LAUNCH_COLLECTION[0];
  const synthetic = {
    releases: {
      [first.id]: ledgerFor(first.id),
      "retired-fixture": [
        { version: "v0", date: "2026-01-15", name: "Retired Fixture", tables: 2,
          rowsLabel: "10 rows", preview: { table: "x.csv", rows: 10, of: 10 }, blockers: [] },
      ],
    },
  };
  const releases = buildReleases(synthetic, [first]);
  assert.equal(releases[first.id].retired, false);
  const retired = releases["retired-fixture"];
  assert.equal(retired.retired, true);
  assert.equal(retired.name, "Retired Fixture");
  assert.equal(retired.version, "v0");
  assert.equal(retired.cadence, null);
  assert.equal(retired.history.length, 1);
  // Not the current release of anything: its preview is not on the shelf.
  assert.ok(!retired.history[0].changed.some((line) => line.includes("downloads from the shelf")));
  const feed = buildFeed(releases);
  const entry = feed.find((item) => item.anchor === "retired-fixture-v0");
  assert.ok(entry, "the retired permalink no longer resolves");
  assert.equal(entry.retired, true);
  assert.equal(entry.name, "Retired Fixture");
  // Sold collections sort ahead of retired ones on a shared date.
  const sameDay = buildFeed(buildReleases({ releases: { ...synthetic.releases, "retired-fixture": [{ ...synthetic.releases["retired-fixture"][0], date: first.updated }] } }, [first]));
  assert.equal(sameDay[0].id, first.id);
});

// The ledger script refuses anything that is not a ledger, and proves it on
// planted files: Codex, PR #53, `{}` was accepted and would have been
// overwritten with the manifest's current releases alone.
test("the ledger script refuses a file that is not a ledger", () => {
  // fileURLToPath, not .pathname. On Windows .pathname yields
  // "/C:/Users/.../Cedar%20Press/..." - a leading slash Node cannot resolve
  // and a percent-encoded space - so this test failed on every Windows
  // checkout whose path contains a space, which is every checkout of this
  // repo. It passed in CI, so the breakage was invisible where it was run.
  const script = fileURLToPath(
    new URL("../../../scripts/record-release.mjs", import.meta.url));
  const dir = mkdtempSync(join(tmpdir(), "cedar-ledger-"));
  const run = (contents) => {
    const path = join(dir, `ledger-${Math.random().toString(36).slice(2)}.json`);
    if (contents !== null) writeFileSync(path, contents);
    const result = spawnSync(process.execPath, [script, "--check", `--ledger=${path}`], { encoding: "utf8" });
    return { status: result.status, stderr: result.stderr, path };
  };
  for (const [label, contents] of [
    ["truncated JSON", "{broken"],
    ["an empty object", "{}"],
    ["a null releases map", '{"releases": null}'],
    ["an array", "[]"],
    ["releases as a list", '{"releases": []}'],
    ["an entry that is not a list", '{"releases": {"funding": {"version": "v0"}}}'],
  ]) {
    const { status, stderr } = run(contents);
    assert.equal(status, 1, `${label} was accepted`);
    assert.match(stderr, /Refusing to rebuild/, label);
  }
  // A missing file starts a new ledger, and `--check` then reports it behind.
  const missing = run(null);
  assert.equal(missing.status, 1);
  assert.doesNotMatch(missing.stderr, /Refusing to rebuild/);
  // The real ledger, copied, is current.
  const real = readFileSync(new URL("../../../data/cedar/releases.json", import.meta.url), "utf8");
  const current = run(real);
  assert.equal(current.status, 0, current.stderr);
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
// The FIRST release describes what the manifest measured WHEN IT WAS RECORDED;
// the LATEST describes what it measures now. Those were the same sentence while
// every collection had exactly one release, and this test asserted it as one.
//
// On 2026-09-04 all twelve went to v1 and they stopped being the same: the
// ledger is append-only, so v0 keeps its own facts forever - that is the point
// of it - while the manifest moved on. legislation went 149,293 -> 206,354 rows,
// and the old assertion read that as a defect rather than as history.
test("the first release keeps its own facts, the latest matches the manifest", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const first = releaseFor(dataset.id).history.at(-1);
    assert.equal(first.kind, RELEASE_KIND.DATA);
    assert.ok(first.changed.length >= 2, dataset.id);
    assert.match(first.changed[0], /^First release on Cedar Press: /);
    // it states SOME measured row count - its own, not necessarily today's
    assert.match(first.changed[0], /[\d,]+ rows|row count unresolved/,
                 `${dataset.id}: ${first.changed[0]}`);
    // and the ledger's NEWEST release is the version the manifest is on.
    // (latestRelease returns a release - kind, changed, version - not the raw
    // ledger entry, so there is no rowsLabel on it to compare.)
    const latest = latestRelease(dataset.id);
    assert.ok(latest, dataset.id);
    assert.equal(latest.version, dataset.version,
                 `${dataset.id}: ledger's newest release is not the manifest's version`);
  }
  // The collection that had no preview file said so rather than promising one.
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
  // The SHAPE, not the day. Pinning this to "Sept. 2" made a routine data
  // refresh fail a formatting test, which teaches the next person to edit the
  // date rather than read the failure.
  assert.match(freshnessLine("funding"),
               /^Updated [A-Z][a-z]+\.? \d{1,2} · monthly$/);
  assert.equal(freshnessLine("not-a-collection"), "");
  assert.equal(latestRelease("nest").version, releaseFor("nest").version);
  assert.equal(latestRelease("not-a-collection"), null);
});
