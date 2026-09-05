// Shape the Research on the client: the seed is well formed, the words are
// there for every type and status, and the related-priority search gives
// the same answers as the service's (the same cases as
// server/tests/test_priorities.py, with the same expected results).

import assert from "node:assert/strict";
import test from "node:test";

import {
  EXPIRY_MONTHS,
  POINTS_PER_ACTIVE_MONTH,
  PRIORITY_STATUSES,
  PRIORITY_TYPES,
  SEED_PRIORITIES,
  byType,
  describeActivity,
  earningLine,
  formatMonth,
  published,
  related,
  relatedness,
  sortPriorities,
  statusLabel,
  tokens,
} from "./pressPriorities.js";

test("the seed is the owner's list, well formed, with both kinds of priority", () => {
  assert.deepEqual(POINTS_PER_ACTIVE_MONTH, { press: 1, press_pro: 2 });
  assert.equal(EXPIRY_MONTHS, 12);
  assert.ok(SEED_PRIORITIES.length >= 11);
  const ids = new Set(SEED_PRIORITIES.map((p) => p.id));
  assert.equal(ids.size, SEED_PRIORITIES.length);
  for (const p of SEED_PRIORITIES) {
    assert.ok(PRIORITY_TYPES[p.type], `${p.id}: unknown type ${p.type}`);
    assert.ok(PRIORITY_STATUSES.some((s) => s.id === p.status), `${p.id}: unknown status ${p.status}`);
    assert.ok(p.title && p.description);
    assert.equal(p.points, 0);
  }
  assert.ok(byType(SEED_PRIORITIES, "research_question").length >= 4);
  assert.ok(byType(SEED_PRIORITIES, "dataset").length >= 7);
  assert.equal(statusLabel("data_construction_underway"), "Data construction underway");
});

test("a request reads as the priority it is about, as the service reads it", () => {
  const text = "I wish you had a dataset showing which tribal enterprises own which subsidiaries";
  assert.equal(related(text)[0].id, "ds-enterprise-ownership");
  assert.deepEqual(related("the weather in Paris"), []);
  assert.deepEqual(related(""), []);
  assert.deepEqual([...tokens("I wish you had a Dataset showing Tribal ENTERPRISES")].sort(), ["enterprises", "tribal"]);
  assert.equal(relatedness("nothing", { title: "", description: "" }), 0);
});

test("priorities sort by points, then subscribers, then title, and the published ones are findable", () => {
  const list = [
    { id: "b", title: "B", points: 3, subscribers: 1, status: "interest" },
    { id: "a", title: "A", points: 3, subscribers: 2, status: "published" },
    { id: "c", title: "C", points: 5, subscribers: 1, status: "interest" },
  ];
  assert.deepEqual(sortPriorities(list).map((p) => p.id), ["c", "a", "b"]);
  assert.deepEqual(published(list).map((p) => p.id), ["a"]);
});

test("the words: months, activity lines and the earning rule per plan", () => {
  assert.equal(formatMonth("2026-09"), "Sept. 2026");
  assert.equal(formatMonth("2026-01"), "Jan. 2026");
  assert.equal(describeActivity({ amount: 2, reason: "monthly_activity" }), "+2 · Active month");
  assert.equal(describeActivity({ amount: -1, reason: "allocation", title: "Tribal enterprise ownership" }), "−1 · Tribal enterprise ownership");
  assert.equal(describeActivity({ amount: -1, reason: "expiration" }), "−1 · Expired after twelve months");
  assert.match(earningLine("press_pro"), /Earn 2 points in each month/);
  assert.match(earningLine("press"), /Earn 1 point in each month/);
  assert.match(earningLine("grove"), /does not earn/);
});
