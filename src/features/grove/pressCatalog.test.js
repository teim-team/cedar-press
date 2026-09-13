// The catalog's own claims: the counts its copy states, the taxonomy that
// organizes it and the storefront predicate the pages filter on.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { LAUNCH_COLLECTION, collectionShort } from "./collection.js";

import {
  GROVE_INCLUDES,
  PRESS_CATALOG,
  PRESS_TAXONOMY,
  PRESS_TIERS,
  STOREFRONT_CATALOG,
  STOREFRONT_SHELVES,
  collectionsOnShelf,
  groupOf,
  isOnStorefront,
  shelfCount,
  spellCount,
} from "./pressCatalog.js";

// "Six collections" was typed beside a shelf of six, and the two could only
// stay equal by luck. The copy now spells the count the catalog adds up to.
test("the tier copy states the counts the catalog adds up to", () => {
  const press = PRESS_TIERS.find((tier) => tier.id === "press");
  const pro = PRESS_TIERS.find((tier) => tier.id === "press_pro");
  const standard = collectionsOnShelf("standard").length;
  const total = shelfCount("pro");
  assert.equal(shelfCount("standard"), standard);
  assert.equal(total, standard + collectionsOnShelf("pro").length);
  assert.ok(press.coverageNote.startsWith(`${spellCount(standard)[0].toUpperCase()}${spellCount(standard).slice(1)} collections`), press.coverageNote);
  assert.ok(pro.promise.startsWith(`${spellCount(collectionsOnShelf("pro").length)[0].toUpperCase()}${spellCount(collectionsOnShelf("pro").length).slice(1)} more collections`), pro.promise);
  assert.ok(pro.coverageNote.startsWith(`${spellCount(total)[0].toUpperCase()}${spellCount(total).slice(1)} collections`), pro.coverageNote);
  // Cedar Grove reaches the whole storefront.
  assert.equal(shelfCount("grove"), PRESS_CATALOG.length);
  // Every finished string is a string: no function leaks to a page.
  for (const tier of PRESS_TIERS) {
    assert.equal(typeof tier.promise, "string", tier.id);
    assert.equal(typeof tier.coverageNote, "string", tier.id);
  }
});

// The pro promise names its collections in prose, so the prose has to name
// every one of them. Pinned by a keyword per collection, so a seventh
// pro-shelf collection cannot arrive unmentioned.
test("the Cedar Press+ promise names every pro-shelf collection", () => {
  const pro = PRESS_TIERS.find((tier) => tier.id === "press_pro").promise.toLowerCase();
  const mention = {
    contractors: "contracting",
    subcontracting: "subcontracting",
    "natural-resources": "resource revenue",
    owned: "individually owned native businesses",
    need: "enterprise structures",
    nonprofits: "nonprofit",
  };
  for (const entry of collectionsOnShelf("pro")) {
    assert.ok(mention[entry.id], `${entry.id} has no keyword to look for; add one`);
    assert.ok(pro.includes(mention[entry.id]), `${entry.id} is not named in "${pro}"`);
  }
});

test("spellCount spells the small numbers and falls back to digits", () => {
  assert.equal(spellCount(0), "no");
  assert.equal(spellCount(6), "six");
  assert.equal(spellCount(12), "twelve");
  assert.equal(spellCount(13), "13");
});

// Subject first, access second: every storefront collection has one home in
// the taxonomy, and the taxonomy names nothing the storefront does not sell.
test("the taxonomy is a partition of the storefront", () => {
  const placed = PRESS_TAXONOMY.flatMap((group) => group.collections);
  assert.equal(new Set(placed).size, placed.length, "a collection is in two groups");
  assert.deepEqual([...placed].sort(), STOREFRONT_CATALOG.map((entry) => entry.id).sort());
  for (const entry of STOREFRONT_CATALOG) {
    assert.ok(groupOf(entry.id), `${entry.id} has no subject group`);
  }
  assert.equal(groupOf("not-a-collection"), null);
  for (const group of PRESS_TAXONOMY) {
    assert.ok(group.name && group.lede, group.id);
    assert.ok(group.collections.length > 0, `${group.id} is empty`);
  }
});

test("the storefront predicate is the shelf list", () => {
  assert.deepEqual([...STOREFRONT_SHELVES], ["standard", "pro"]);
  assert.equal(isOnStorefront({ shelf: "standard" }), true);
  assert.equal(isOnStorefront({ shelf: "pro" }), true);
  assert.equal(isOnStorefront({ shelf: "grove" }), false);
  assert.equal(isOnStorefront(null), false);
  assert.deepEqual(STOREFRONT_CATALOG, PRESS_CATALOG.filter(isOnStorefront));
});

// The Grove rollup counts the shelf it summarises.
test("the Press+ rollup spells the pro shelf's count", () => {
  const rollup = GROVE_INCLUDES.find((entry) => entry.id === "all-pro");
  assert.ok(rollup.blurb.startsWith(`The ${spellCount(collectionsOnShelf("pro").length)} specialized`), rollup.blurb);
});

test("the structured data and the sitemap are generated from the catalog and are current", () => {
  const script = fileURLToPath(new URL("../../../scripts/seo-head.mjs", import.meta.url));
  const run = spawnSync(process.execPath, [script, "--check"], { encoding: "utf8" });
  assert.equal(run.status, 0, `${run.stdout}\n${run.stderr}\nrun: node scripts/seo-head.mjs`);
});

// ── The storefront's display name wins ─────────────────────────────────────
//
// A collection is named twice: the workspace descriptor says what it IS
// (`short_name`), the storefront catalog says how it is NAMED to a reader
// (`short`). Where they differ the catalog wins, and `collectionShort()` is
// the one place that resolves it. `shelf.py` always did; the JavaScript and
// `collections.py` both read the descriptor directly, so the two sides agreed
// on the wrong answer and the cross-language parity test was satisfied by it.

test("NEED is named Cedar NEED everywhere a short name is shown", () => {
  // docs/NEED_RENAME_2026-09-10.md: the Minneapolis Fed publishes a dataset
  // under close to this description, so a bare "Native Entity Enterprise
  // Dataset" invites a reader to assume ours is theirs. The formal name was
  // renamed to lead with Cedar for that reason. The short name is what every
  // compact surface actually shows -- the door's strip, the frame's rail, the
  // shelf, the collection picker, and the basis line under a figure -- and it
  // was still bare.
  const need = PRESS_CATALOG.find((entry) => entry.id === "need");
  assert.equal(need.short, "Cedar NEED");
  assert.match(need.name, /^Cedar /);

  const dataset = LAUNCH_COLLECTION.find((entry) => entry.id === "need");
  assert.equal(dataset.shortName, "NEED", "the descriptor is the workspace's; only the catalog is ours to name");
  assert.equal(collectionShort(dataset), "Cedar NEED");
});

test("a short name shown to a reader is never a bare acronym of a Cedar name", () => {
  // The general rule behind the case above: if the formal name leads with
  // Cedar because the bare description is ambiguous, the short name may not
  // then drop it. Catches the next collection named this way.
  for (const entry of STOREFRONT_CATALOG) {
    if (!entry.short || !entry.name.startsWith("Cedar ")) continue;
    const acronym = entry.name.match(/\(([A-Z]{2,})\)$/)?.[1];
    if (!acronym) continue;
    assert.notEqual(
      entry.short,
      acronym,
      `${entry.id}: the formal name leads with Cedar and the short name is the bare acronym "${acronym}"`,
    );
  }
});

test("collectionShort prefers the catalog and falls back to the descriptor", () => {
  const byId = new Map(PRESS_CATALOG.map((entry) => [entry.id, entry]));
  for (const dataset of LAUNCH_COLLECTION) {
    const expected = byId.get(dataset.id)?.short ?? dataset.shortName;
    assert.equal(collectionShort(dataset), expected, dataset.id);
  }
  assert.equal(collectionShort(null), null);
  // A collection the storefront does not carry keeps the descriptor's name.
  assert.equal(collectionShort({ id: "not-on-the-shelf", shortName: "X" }), "X");
});
