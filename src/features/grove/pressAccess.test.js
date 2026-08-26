// Cedar Press access. Two rungs of one standalone product, plus a shelf that
// belongs to a different product entirely, so the interesting cases are the
// boundaries: what Standard cannot open, and what no Cedar Press plan opens.

import assert from "node:assert/strict";
import test from "node:test";

import { LAUNCH_COLLECTION } from "./collection.js";
import {
  NATIVE_LINKAGE,
  PRESS_CATALOG,
  PRESS_CATALOG_BY_ID,
  PRESS_HISTORY_FROM,
  PRESS_TIERS,
  collectionsOnShelf,
} from "./pressCatalog.js";
import {
  SHELF,
  canOpenDataset,
  canReadCedarPress,
  historyFor,
  shelfReach,
  upgradeFor,
} from "./pressAccess.js";

const as = (tier) => (tier ? { workspace_tier: tier } : null);

test("both Cedar Press rungs read the page", () => {
  assert.equal(canReadCedarPress(as("press")), true);
  assert.equal(canReadCedarPress(as("press_pro")), true);
  assert.equal(canReadCedarPress({ workspaceTier: "press_pro" }), true);
});

// The session payload carries the server's resolution as `user.press`, and
// when it is present it wins over the local tier map: a lapsed subscription
// the server knows about must close the page whatever tier string the
// payload still carries beside it.
test("the server's resolution wins over the local tier map", () => {
  const lapsed = { workspace_tier: "press_pro", press: { canRead: false, shelfReach: null } };
  assert.equal(canReadCedarPress(lapsed), false);
  assert.equal(shelfReach(lapsed), null);
  const granted = { workspace_tier: "free", press: { canRead: true, shelfReach: SHELF.PRO } };
  assert.equal(canReadCedarPress(granted), true);
  assert.equal(shelfReach(granted), SHELF.PRO);
  // An unrecognized reach from a newer server reaches nothing rather than
  // guessing, the same safe answer as an unknown tier.
  assert.equal(shelfReach({ press: { canRead: true, shelfReach: "penthouse" } }), null);
});

// Cedar Press is sold through Tribal Business News and is not included with
// Cedar Grove or with Tree. This used to pass grove and tree.
test("Cedar Grove does not include Cedar Press", () => {
  assert.equal(canReadCedarPress(as("grove")), false);
});

test("the platform ladder does not include Cedar Press at any rung", () => {
  for (const tier of ["free", "sprout", "sapling", "tree"]) {
    assert.equal(canReadCedarPress(as(tier)), false, tier);
  }
});

test("an absent or unknown tier reads nothing", () => {
  for (const user of [null, undefined, {}, { workspace_tier: "bogus" }]) {
    assert.equal(canReadCedarPress(user), false);
    assert.equal(shelfReach(user), null);
  }
});

test("the shelves nest upward", () => {
  assert.equal(shelfReach(as("press")), SHELF.STANDARD);
  assert.equal(shelfReach(as("press_pro")), SHELF.PRO);
  assert.equal(shelfReach(as("grove")), SHELF.GROVE);
});

test("Standard opens the standard shelf and nothing above it", () => {
  const standard = { shelf: SHELF.STANDARD };
  const pro = { shelf: SHELF.PRO };
  const grove = { shelf: SHELF.GROVE };
  assert.equal(canOpenDataset(as("press"), standard), true);
  assert.equal(canOpenDataset(as("press"), pro), false);
  assert.equal(canOpenDataset(as("press"), grove), false);
});

test("Pro opens standard and pro, and still not the Grove shelf", () => {
  assert.equal(canOpenDataset(as("press_pro"), { shelf: SHELF.STANDARD }), true);
  assert.equal(canOpenDataset(as("press_pro"), { shelf: SHELF.PRO }), true);
  assert.equal(canOpenDataset(as("press_pro"), { shelf: SHELF.GROVE }), false);
});

test("Cedar Grove opens every shelf", () => {
  for (const shelf of Object.values(SHELF)) {
    assert.equal(canOpenDataset(as("grove"), { shelf }), true, shelf);
  }
});

// An entry nobody has classified must not fall open to the cheapest plan.
test("a dataset with no shelf defaults closed to Standard", () => {
  assert.equal(canOpenDataset(as("press"), {}), false);
  assert.equal(canOpenDataset(as("press"), { shelf: "nonsense" }), false);
  assert.equal(canOpenDataset(as("press_pro"), {}), true);
});

test("nobody without a plan opens anything", () => {
  for (const shelf of Object.values(SHELF)) {
    assert.equal(canOpenDataset(null, { shelf }), false, shelf);
    assert.equal(canOpenDataset(as("tree"), { shelf }), false, shelf);
  }
});

// The prompt has to name a product. A Grove-only dataset is never opened by a
// higher rung of Cedar Press, so it must not offer one.
test("the upgrade prompt names the product that actually opens the shelf", () => {
  assert.deepEqual(upgradeFor({ shelf: SHELF.PRO }), {
    id: "press_pro",
    name: "Cedar Press+",
    sameProduct: true,
  });
  assert.deepEqual(upgradeFor({ shelf: SHELF.GROVE }), {
    id: "grove",
    name: "Cedar Grove",
    sameProduct: false,
  });
  assert.equal(upgradeFor({}).id, "press_pro");
});

// The catalog is the only place a shelf is declared. A shipping dataset that
// is not in it would resolve to Pro by the unclassified rule and quietly
// disappear from Standard, which is a pricing bug nobody would see in review.
test("every shipping dataset is placed in the catalog", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    assert.ok(PRESS_CATALOG_BY_ID[dataset.id], `${dataset.id} is not in the catalog`);
  }
});

test("every catalog entry sits on a shelf the model knows", () => {
  const known = new Set(Object.values(SHELF));
  for (const entry of PRESS_CATALOG) {
    assert.ok(known.has(entry.shelf), `${entry.id}: ${entry.shelf}`);
    assert.ok(entry.name && entry.blurb, entry.id);
  }
});

// If every collection were on one shelf the upgrade would have nothing to
// point at, which is a launch mistake worth catching in CI rather than a demo.
test("the catalog spans all three shelves", () => {
  const shelves = new Set(PRESS_CATALOG.map((entry) => entry.shelf));
  for (const shelf of Object.values(SHELF)) {
    assert.ok(shelves.has(shelf), `nothing on the ${shelf} shelf`);
  }
});

// The second axis. Standard carries the collection but not its whole series.
test("Standard sees a Standard collection from the Press window forward", () => {
  const lobbying = PRESS_CATALOG_BY_ID.lobbying;
  const h = historyFor({ workspace_tier: "press" }, lobbying);
  assert.equal(h.from, PRESS_HISTORY_FROM);
  assert.equal(h.full, lobbying.historyFrom);
  assert.equal(h.deeper, true);
});

test("Pro opens the reconstructed series behind a Standard collection", () => {
  const lobbying = PRESS_CATALOG_BY_ID.lobbying;
  const h = historyFor({ workspace_tier: "press_pro" }, lobbying);
  assert.equal(h.from, lobbying.historyFrom);
  assert.equal(h.deeper, false);
});

// Selling depth that does not exist is a promise the data cannot keep. Deals
// is the collection whose whole archive begins at the Press window itself, so
// there is nothing behind it for Cedar Press+ to open.
test("a collection with no archive behind the Press window offers no deeper history", () => {
  const deals = PRESS_CATALOG_BY_ID.deals;
  assert.ok(deals.historyFrom >= PRESS_HISTORY_FROM, "fixture assumption");
  const h = historyFor({ workspace_tier: "press" }, deals);
  assert.equal(h.from, deals.historyFrom);
  assert.equal(h.deeper, false);
  // Cedar Press+ reaches the same year, because that is all there is.
  assert.equal(historyFor({ workspace_tier: "press_pro" }, deals).from, deals.historyFrom);
});

test("a capped collection reports no history for the reader", () => {
  const h = historyFor({ workspace_tier: "press" }, PRESS_CATALOG_BY_ID.contractors);
  assert.equal(h.from, null);
  assert.equal(h.deeper, false);
});

// Gaming is the reason to cross the second line, so what it may show without
// Cedar Grove is a declared list rather than a component's judgement.
test("the Grove-exclusive collection declares what it shows and withholds", () => {
  const gaming = PRESS_CATALOG_BY_ID.gaming;
  assert.equal(gaming.shelf, SHELF.GROVE);
  assert.ok(gaming.preview.shows.length > 0);
  assert.ok(gaming.preview.withholds.length > 0);
  const shows = gaming.preview.shows.join(" ").toLowerCase();
  const withholds = gaming.preview.withholds.join(" ").toLowerCase();
  assert.match(withholds, /download/);
  assert.match(withholds, /record-level/);
  assert.doesNotMatch(shows, /download/);
});

test("no Cedar Press plan opens the Grove-exclusive collection", () => {
  for (const tier of ["press", "press_pro"]) {
    assert.equal(canOpenDataset({ workspace_tier: tier }, PRESS_CATALOG_BY_ID.gaming), false, tier);
  }
  assert.equal(upgradeFor(PRESS_CATALOG_BY_ID.gaming).sameProduct, false);
});

// The catalog renders one band per tier and fills each band from its shelf,
// so a collection whose shelf no tier claims is simply absent from the page.
// Nothing throws and nothing is visible in review, which is why it is pinned.
test("every collection lands on a shelf some tier carries", () => {
  const shelves = PRESS_TIERS.map((tier) => tier.shelf);
  const shown = shelves.flatMap((shelf) => collectionsOnShelf(shelf));
  for (const entry of PRESS_CATALOG) {
    const times = shown.filter((item) => item.id === entry.id).length;
    assert.equal(times, 1, `${entry.id} appears on ${times} shelves`);
  }
  assert.equal(shown.length, PRESS_CATALOG.length);
});

// A tier with nothing on it renders a band with an empty list beside it.
test("every tier carries at least one collection", () => {
  for (const tier of PRESS_TIERS) {
    assert.ok(collectionsOnShelf(tier.shelf).length > 0, tier.id);
  }
});

// The join to Native entities is what Cedar sells; the underlying records are
// public. The reader panel renders `linkage` per collection and renders
// nothing when it is missing, so a new collection would quietly ship without
// the one line that says why it is worth paying for.
test("every collection states what it is linked to", () => {
  for (const entry of PRESS_CATALOG) {
    assert.ok(entry.linkage && entry.linkage.length > 40, `${entry.id} has no linkage`);
  }
});

test("the linkage tiers stay distinct rather than collapsing into one", () => {
  assert.ok(NATIVE_LINKAGE.claim && NATIVE_LINKAGE.body);
  assert.ok(NATIVE_LINKAGE.tiers.length >= 4);
  const names = NATIVE_LINKAGE.tiers.map((tier) => tier.name);
  assert.equal(new Set(names).size, names.length);
  for (const tier of NATIVE_LINKAGE.tiers) assert.ok(tier.note, tier.name);
  // Native-serving is not Native-owned, and the page must not imply it is.
  const joined = names.join(" ").toLowerCase();
  assert.match(joined, /native-led/);
  assert.match(joined, /native-serving/);
});

// Gaming counterparties are not all Native, and saying otherwise would be a
// claim the data cannot carry.
test("the one collection with non-Native counterparties says so", () => {
  assert.match(PRESS_CATALOG_BY_ID.gaming.linkage, /not all Native/);
});
