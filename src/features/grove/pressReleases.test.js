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
  collectionCitation,
  collectionDeclaredSample,
  collectionSample,
  COUNT_NOT_SHOWN,
  hasSample,
} from "./collection.js";
import { downloadRecord } from "./customerTables.js";
import { PRESS_CATALOG } from "./pressCatalog.js";
import {
  CADENCE,
  connectedReleaseModel,
  previewReleaseModel,
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
test("every released collection has a release and nothing else does", () => {
  assert.deepEqual(
    Object.keys(PRESS_RELEASES).sort(),
    LAUNCH_COLLECTION.map((dataset) => dataset.id).sort(),
  );
  for (const entry of PRESS_CATALOG) {
    // The two presented by their record structure have no release in the
    // manifest, and the feed does not invent one for them.
    if (entry.coverage.kind === "structure") assert.equal(releaseFor(entry.id), null, `${entry.id} has a release it never shipped`);
    else assert.ok(releaseFor(entry.id), `${entry.id} has no release`);
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
    // Dated by the data refresh, not the re-release (2026-10-06 changed no data).
    assert.equal(release.history[0].date, dataset.refreshed ?? dataset.updated, dataset.id);
  }
});

// One date for readers, the data refresh (L1-U05). The release date the
// ledger records is kept as `released` and never shown, and nothing falls
// back to it: a manifest without a refresh date fails here, not on the page.
test("every collection is dated by its data refresh, and its citation carries that date", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    assert.match(dataset.refreshed ?? "", /^\d{4}-\d{2}-\d{2}$/,
                 `${dataset.id}: the manifest records no data refresh date`);
    assert.equal(dataset.updated, dataset.refreshed, dataset.id);
    assert.match(dataset.released, /^\d{4}-\d{2}-\d{2}$/, dataset.id);
    assert.ok(collectionCitation(dataset.id).endsWith(` Updated ${dataset.refreshed}.`), dataset.id);
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
      date: dataset.released,
      name: dataset.name,
      tables: cedar.n_tables,
      // The ledger records the measured label even where the page shows none
      // (COUNT_NOT_SHOWN, collection.js).
      rowsLabel: COUNT_NOT_SHOWN.has(dataset.id) ? record.rowsLabel : dataset.rowsLabel,
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
        assert.ok(record.date <= dataset.released, `${id} ${record.version} is dated after the descriptor`);
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
  // Not the current release of anything: its sample is not downloadable.
  assert.ok(!retired.history[0].changed.some((line) => line.includes("available to download")));
  const feed = buildFeed(releases);
  const entry = feed.find((item) => item.anchor === "retired-fixture-v0");
  assert.ok(entry, "the retired permalink no longer resolves");
  assert.equal(entry.retired, true);
  assert.equal(entry.name, "Retired Fixture");
  // Sold collections sort ahead of retired ones on a shared date.
  const sameDay = buildFeed(buildReleases({ releases: { ...synthetic.releases, "retired-fixture": [{ ...synthetic.releases["retired-fixture"][0], date: first.refreshed ?? first.updated }] } }, [first]));
  assert.equal(sameDay[0].id, first.id);
});

// The ledger script refuses anything that is not a ledger, and proves it on
// planted files: Codex, PR #53, `{}` was accepted and would have been
// overwritten with the manifest's current releases alone.
test("the ledger script refuses a file that is not a ledger", () => {
  // fileURLToPath, not .pathname. On Windows .pathname yields
  // "/C:/<home>/Cedar%20Press/..." - a leading slash Node cannot resolve
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

// Only the current release's sample is a file a reader can download.
test("only the current release says its example records download", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const [current, ...older] = releaseFor(dataset.id).history;
    if (collectionSample(dataset.id)?.path) {
      assert.ok(current.changed.some((line) => line.endsWith("are available to download.")), dataset.id);
    }
    for (const entry of older) {
      assert.ok(!entry.changed.some((line) => / available to download\./.test(line)), `${dataset.id} ${entry.version}`);
    }
    // Reader wording: the feed never speaks the build's vocabulary.
    for (const entry of [current, ...older]) {
      for (const line of entry.changed) {
        assert.ok(!/\b(preview|shelf|manifest|readiness)\b/i.test(line), `${dataset.id} ${entry.version}: ${line}`);
      }
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
// Owner rule 2026-09-28: readers see Updated dates, not release numbers,
// table counts or change history. The ledger keeps every version; a reader
// sees one entry per collection, for the dataset as it stands.
test("each collection shows one entry, for the dataset as it stands", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const history = releaseFor(dataset.id).history;
    assert.equal(history.length, 1, `${dataset.id}: earlier versions are not shown`);
    const [entry] = history;
    assert.equal(entry.kind, RELEASE_KIND.DATA);
    assert.equal(entry.version, dataset.version, dataset.id);
    assert.equal(latestRelease(dataset.id).version, dataset.version, dataset.id);
    // What the collection holds now, never a summed count of earlier tables.
    assert.match(entry.changed[0], /^Current dataset: [\d,]+ observations\.$/, `${dataset.id}: ${entry.changed[0]}`);
    // The example count is the served download's, not the ledger's sample.
    const served = downloadRecord(dataset.id)?.rows;
    if (hasSample(dataset.id) && served) {
      assert.equal(entry.changed[1], `${served} example ${served === 1 ? "record is" : "records are"} available to download.`, dataset.id);
    } else {
      assert.equal(entry.changed[1], "No example records are available yet.", dataset.id);
    }
  }
  // The served downloads that hold fewer than ten rows say so.
  assert.match(releaseFor("federal-register").history[0].changed[1], /^5 example records /);
  assert.match(releaseFor("plot").history[0].changed[1], /^3 example records /);
  // A synthetic collection with no served sample promises none.
  const [first] = LAUNCH_COLLECTION;
  const bare = buildReleases({ releases: { "no-sample": [
    { version: "v0", date: "2026-01-15", name: "No Sample", tables: 1,
      rowsLabel: "7 observations", preview: null, blockers: [] },
  ] } }, [first])["no-sample"];
  assert.deepEqual([...bare.history[0].changed], ["Current dataset: 7 observations.", "No example records are available yet."]);
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
  // The DATA refresh date, not the release date (2026-10-06), and the
  // cadence worded as a schedule.
  assert.match(freshnessLine("funding"),
               /^Data as of [A-Z][a-z]+\.? \d{1,2} · weekly review schedule$/);
  assert.ok(releaseFor("funding").refreshed, "a sold collection carries its data refresh date");
  assert.ok(releaseFor("funding").refreshed <= releaseFor("funding").updated,
            "data cannot be refreshed after the release that carries it");
  assert.equal(freshnessLine("not-a-collection"), "");
  assert.equal(latestRelease("need").version, releaseFor("need").version);
  assert.equal(latestRelease("not-a-collection"), null);
});


function currentFixture() {
  const version = "a".repeat(64);
  return { source: "verified_current", history_complete: false, releases: [{
    id: "funding", name: "Funding", version, updated: null, retired: false,
    history: [{ version, date: null, date_basis: "not_recorded", kind: "data", changed: ["Available observations."] }],
  }] };
}

test("current feed never borrows publication dates or aggregate totals from public previews", () => {
  const model = connectedReleaseModel(currentFixture());
  assert.equal(model.source, "verified_current");
  assert.equal(model.historyComplete, false);
  assert.equal(model.feed.length, 1);
  assert.equal(model.feed[0].date, null);
  assert.equal(model.feed[0].anchor, `funding-${"a".repeat(64)}`);
  // No earlier update dates beside the current facts (owner rule 2026-09-28).
  assert.deepEqual(model.previewHistory, []);
  const preview = previewReleaseModel();
  assert.equal(preview.source, "public_preview");
  assert.deepEqual(preview.feed.map((item) => item.anchor), RELEASE_FEED.map((item) => item.anchor));
});

test("invalid live response cannot masquerade as a release feed", () => {
  const invalid = [null, { releases: [] }];
  for (const mutate of [
    (p) => p.releases.push(p.releases[0]),
    (p) => { p.releases[0].id = "infrastructure"; },
    (p) => { p.releases[0].id = "__proto__"; },
    (p) => { p.releases[0].updated = "2026-10-03"; },
    (p) => { p.releases[0].history[0].date = "2026-10-03"; },
    (p) => { p.releases[0].version = "v3"; },
    (p) => { p.releases[0].record_count = -1; },
    (p) => { p.releases[0].preview_updated = "2026-02-30"; },
  ]) { const fixture = currentFixture(); mutate(fixture); invalid.push(fixture); }
  for (const value of invalid) assert.throws(() => connectedReleaseModel(value));
});

test("activity excludes undated current entries and future dates", () => {
  const current = connectedReleaseModel(currentFixture()).feed[0];
  const activity = recentActivity(30, new Date("2026-10-03T12:00:00Z"), [
    { ...current, date: "2026-12-01" }, current, { ...current, date: "2026-10-01" },
  ]);
  assert.equal(activity.releases, 1);
  assert.equal(activity.latest, "2026-10-01");
});
