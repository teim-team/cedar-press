// The catalog's own claims: the counts its copy states, the taxonomy that
// organizes it and the storefront predicate the pages filter on.

import assert from "node:assert/strict";
import test from "node:test";

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
    nest: "enterprise structures",
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
