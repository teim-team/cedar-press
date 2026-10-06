// Shape the Research on the client: the seed is well formed, the words are
// there for every type and status, and the related-priority search gives
// the same answers as the service's (the same cases as
// server/tests/test_priorities.py, with the same expected results).

import assert from "node:assert/strict";
import test from "node:test";

import {
  createPrioritySession,
  visiblePriorityState,
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

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test("submitted requests are cancelled with the account and are never retried", async () => {
  const result = deferred();
  let writes = 0;
  let signal;
  const session = createPrioritySession({
    fetchPriorities: () => assert.fail("an old request must not refresh a new account"),
    fetchInfluence: () => assert.fail("no balance read expected"),
    submitResearchRequest: (args) => { writes += 1; signal = args.signal; return result.promise; },
    publish: () => assert.fail("no stale publication expected"),
  });
  const pending = session.submit({ text: "Please expand the source coverage", supportPoints: 1 });
  session.dispose();
  assert.equal(signal.aborted, true);
  result.resolve({ id: 42 });
  await assert.rejects(pending, { name: "AbortError" });
  assert.equal(writes, 1);
});

test("private points are hidden immediately on logout, plan change or same-email re-login", () => {
  const first = { email: "reader@example.org", tier: "press_pro" };
  const old = { owner: first, status: "ok", priorities: [{ id: "private" }], influence: { points_available: 7 } };
  assert.equal(visiblePriorityState(old, first, { connected: true, enabled: true }), old);
  for (const owner of [null, { ...first }, { ...first, tier: "press" }]) {
    const value = visiblePriorityState(old, owner, { connected: true, enabled: Boolean(owner) });
    assert.equal(value.influence, null);
    assert.deepEqual(value.priorities, []);
    assert.equal(value.status, owner ? "loading" : "signed-out");
  }
  const offline = visiblePriorityState(old, first, { connected: false, enabled: true });
  assert.equal(offline.status, "static");
  assert.equal(offline.influence, null);
});

test("disposed account reads cannot restore balances even when transport ignores abort", async () => {
  const list = deferred();
  const card = deferred();
  const states = [];
  let signal;
  const session = createPrioritySession({ fetchPriorities: (options) => { signal = options.signal; return list.promise; },
    fetchInfluence: () => card.promise, movePoints: () => assert.fail("no mutation expected"), publish: (state) => states.push(state) });
  const pending = session.reload();
  session.dispose();
  assert.equal(signal.aborted, true);
  list.resolve({ priorities: [{ id: "old-account" }] });
  card.resolve({ points_available: 8 });
  await pending;
  assert.deepEqual(states, []);
});

test("only the latest points refresh can publish and failures clear stale private totals", async () => {
  const oldList = deferred();
  const oldCard = deferred();
  let reads = 0;
  let cards = 0;
  let fail = false;
  const states = [];
  const session = createPrioritySession({
    fetchPriorities: () => ++reads === 1 ? oldList.promise : fail ? Promise.reject(new Error("Unavailable")) : Promise.resolve({ priorities: [{ id: "current" }] }),
    fetchInfluence: () => ++cards === 1 ? oldCard.promise : Promise.resolve({ points_available: 2 }),
    movePoints: () => assert.fail("no mutation expected"), publish: (state) => states.push(state),
  });
  const older = session.reload();
  await session.reload();
  oldList.resolve({ priorities: [{ id: "stale" }] });
  oldCard.resolve({ points_available: 99 });
  await older;
  assert.equal(states.length, 1);
  assert.equal(states[0].influence.points_available, 2);
  fail = true;
  await session.reload();
  assert.equal(states.at(-1).status, "failed");
  assert.equal(states.at(-1).influence, null);
  assert.deepEqual(states.at(-1).priorities, []);
  session.dispose();
});

test("an allocation finishes against its own session once and cannot refresh a new account", async () => {
  const debit = deferred();
  let writes = 0;
  let reads = 0;
  let signal;
  const states = [];
  const session = createPrioritySession({
    fetchPriorities: async () => { reads += 1; return { priorities: [] }; },
    fetchInfluence: async () => ({ points_available: 1 }),
    movePoints: (args) => { writes += 1; signal = args.signal; assert.equal(args.points, 1); return debit.promise; },
    publish: (state) => states.push(state),
  });
  const pending = session.move("a-priority", 1);
  session.dispose();
  assert.equal(signal.aborted, true);
  debit.resolve({ points_available: 0 });
  await assert.rejects(pending, { name: "AbortError" });
  assert.equal(writes, 1, "a possibly committed debit must never be retried automatically");
  assert.equal(reads, 0);
  assert.deepEqual(states, []);
  await assert.rejects(session.move("a-priority", 1), { name: "AbortError" });
  assert.equal(writes, 1);
});

test("successful allocations re-read authoritative balances and malformed responses stay unavailable", async () => {
  const states = [];
  let malformed = false;
  const session = createPrioritySession({
    fetchPriorities: async () => ({ priorities: [] }),
    fetchInfluence: async () => ({ points_available: malformed ? "many" : 1 }),
    movePoints: async () => ({ points_available: 999, priority: { points: 999 } }),
    publish: (state) => states.push(state),
  });
  await session.move("a-priority", 1);
  assert.equal(states.at(-1).influence.points_available, 1, "use the authoritative reread, not optimistic mutation totals");
  malformed = true;
  await session.reload();
  assert.equal(states.at(-1).status, "failed");
  assert.equal(states.at(-1).influence, null);
  session.dispose();
});
