// Dump the JavaScript access rules as JSON, so the Python implementation can
// be compared against them key for key.
//
//   node scripts/dump-access.mjs > /tmp/access.json
//
// WHY THIS EXISTS
// `src/features/grove/pressAccess.js` decides what renders and
// `server/cedar_press/repository.py` decides what is served, and both files
// say in their own comments that they must answer identically. Nothing
// compared them, and they had drifted by exactly one tier: `tree` was in the
// server's SHELF_BY_TIER and missing from the client's PLAN_REACH, so a Tree
// subscriber was served twelve collections by the API and shown none of them
// in the browser. `press_catalog.py` also claimed for months that "the
// JavaScript and this can be compared as sets by the parity test" while no
// such test existed.
//
// This is the dump for that comparison. It covers the two questions the
// access rules answer separately -- which plans are sold the Cedar Press page,
// and which shelves each plan reaches -- because conflating them is what
// produced the drift, and a check that reads only one of them would have
// passed through it.
//
// Executed by `server/tests/test_access.py`, which runs in the same CI job as
// the rest of the Python suite and after `npm ci`, so `node` is present. The
// output is flat and sorted for the same reason `dump-collection.mjs`'s is: a
// mismatch should read as "this tier, this key".

import { EXCLUDED_COLLECTIONS } from "../src/features/grove/collection.js";
import { PLAN_REACH, SHELF, canReadCedarPress, shelfReach } from "../src/features/grove/pressAccess.js";
import { PRESS_CATALOG } from "../src/features/grove/pressCatalog.js";
import { WORKSPACE_TIERS } from "../src/workspaceTier.js";

// Every tier the product recognizes, not only the ones with a Press answer.
// A tier that reaches nothing is a value the Python side must also produce,
// and a dump that omitted it would let a new tier open the page on one side.
const TIERS = Object.keys(WORKSPACE_TIERS).sort();

const asUser = (tier) => ({ workspace_tier: tier });

const byShelf = {};
for (const entry of PRESS_CATALOG) {
  (byShelf[entry.shelf] ??= []).push(entry.id);
}
for (const ids of Object.values(byShelf)) ids.sort();

process.stdout.write(
  JSON.stringify(
    {
      tiers: TIERS,
      shelves: SHELF,
      // The raw map, so a missing key is reported as a missing key rather
      // than only as a wrong answer for one tier.
      planReach: PLAN_REACH,
      // The resolved answers, which is what the two products actually have to
      // agree on. `shelfReach` folds in the unknown-tier fallback that
      // PLAN_REACH alone does not show.
      shelfReach: Object.fromEntries(TIERS.map((t) => [t, shelfReach(asUser(t))])),
      canReadCedarPress: Object.fromEntries(
        TIERS.map((t) => [t, canReadCedarPress(asUser(t))]),
      ),
      // The Press/Grove content split as the catalog states it. Compared
      // against the collections manifest, whose `excluded` entries carry the
      // shelf the Cedar data workspace assigned.
      catalogByShelf: Object.fromEntries(Object.entries(byShelf).sort()),
      excluded: EXCLUDED_COLLECTIONS.map((entry) => ({
        id: entry.id,
        shelf: entry.shelf,
      })),
    },
    null,
    2,
  ),
);
