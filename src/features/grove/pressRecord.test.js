// The record page's address, its way back, and the one derivation it makes.
//
// These are the three things the viewer and the record page have to agree
// about. Each assertion below is a way they went wrong, or could: a record
// whose table declares no id addressed by a position that meant something
// different under a different cut; a scroll restored onto a result the reader
// had since re-filtered; an "in real dollars" figure with no year on it.
import assert from "node:assert/strict";
import test from "node:test";

import {
  findRecord,
  neighbours,
  readRecordParams,
  realDollars,
  recordHref,
  rememberReturn,
  resultsHref,
  takeReturn,
} from "./pressRecord.js";

/** A session storage the tests own, since node has no window. */
function fakeWindow() {
  const map = new Map();
  global.window = {
    sessionStorage: {
      getItem: (k) => (map.has(k) ? map.get(k) : null),
      setItem: (k, v) => map.set(k, String(v)),
      removeItem: (k) => map.delete(k),
    },
  };
  return () => { delete global.window; };
}

test("an address carries the table, the record and the cut it came from", () => {
  const href = recordHref({ key: "funding/federal_funding_transactions", recordId: "8635_B07", from: "c=funding&q=block" });
  const url = new URL(href, "https://cedarpress.ai");
  assert.equal(url.pathname, "/record");
  assert.equal(url.searchParams.get("k"), "funding/federal_funding_transactions");
  assert.equal(url.searchParams.get("r"), "8635_B07");
  assert.equal(url.searchParams.get("from"), "c=funding&q=block");
  // And it survives the round trip, ids with spaces and slashes included.
  const odd = recordHref({ key: "deals/deals_classified", recordId: "D 1/2" });
  assert.equal(readRecordParams(new URL(odd, "https://x").search).recordId, "D 1/2");
});

test("a table with no declared id is addressed by position, and never by both", () => {
  const byIndex = recordHref({ key: "need/need_enterprises", index: 3 });
  assert.match(byIndex, /i=3/);
  // An id wins where there is one: two addresses for one record would be two
  // pages for one record.
  const both = recordHref({ key: "need/need_enterprises", recordId: "E-1", index: 3 });
  assert.match(both, /r=E-1/);
  assert.doesNotMatch(both, /i=3/);
});

test("the way back is the results, and the bare page without a cut", () => {
  assert.equal(resultsHref("c=funding&p=2"), "/data?c=funding&p=2");
  assert.equal(resultsHref(""), "/data");
});

test("the scroll is returned once, and only to the result it was written for", () => {
  const done = fakeWindow();
  try {
    rememberReturn({ search: "c=funding&p=2", y: 1840 });
    // A different cut is a different result: the top of the page is better
    // than the scroll position of a result that no longer exists.
    assert.equal(takeReturn("?c=deals"), null);
    rememberReturn({ search: "c=funding&p=2", y: 1840 });
    assert.deepEqual(takeReturn("?c=funding&p=2"), { y: 1840 });
    // One shot: a later arrival at the same URL starts at the top.
    assert.equal(takeReturn("?c=funding&p=2"), null);
  } finally {
    done();
  }
});

test("neighbours are the reader's own ordering, and the ends have none", () => {
  const items = [{ id: "a" }, { id: "b" }, { id: "c" }];
  const middle = neighbours(items, "b");
  assert.equal(middle.at, 1);
  assert.equal(middle.of, 3);
  assert.equal(middle.previous.id, "a");
  assert.equal(middle.next.id, "c");
  assert.equal(neighbours(items, "a").previous, null);
  assert.equal(neighbours(items, "c").next, null);
  // A record the cut filters out is not in the walk at all.
  assert.equal(neighbours(items, "zz").at, -1);
});

test("a record that is not in the sample is not a neighbouring record", () => {
  const items = [
    { id: "k:1", recordId: "1", index: 0 },
    { id: "k:2", recordId: "2", index: 1 },
  ];
  assert.equal(findRecord(items, { recordId: "2" }).id, "k:2");
  assert.equal(findRecord(items, { recordId: "9" }), null);
  assert.equal(findRecord(items, { index: 1 }).id, "k:2");
  assert.equal(findRecord(items, { index: 9 }), null);
  assert.equal(findRecord(items, {}), null);
});

test("the adjusted amount is read from the file, with the year it is in", () => {
  const row = { obligated_usd: "500000.00", obligated_usd_real2025: "732727.0", inflation_base_year: "2025" };
  assert.deepEqual(realDollars(row, "obligated_usd"), { column: "obligated_usd_real2025", value: 732727, year: "2025" });
  // No such column, no second figure: the page never deflates anything itself.
  assert.equal(realDollars({ obligated_usd: "500000" }, "obligated_usd"), null);
  // The column's own suffix is the fallback year, so a figure is never shown
  // without one.
  assert.equal(realDollars({ spend_usd: "10", spend_usd_real2019: "12" }, "spend_usd").year, "2019");
  // A blank adjusted cell is not zero dollars.
  assert.equal(realDollars({ a: "1", a_real2025: "" }, "a"), null);
});
