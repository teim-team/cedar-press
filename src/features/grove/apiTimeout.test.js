// The API client's deadline (api.js, REQUEST_TIMEOUT_MS).
//
// A stalled request used to leave the session check, an article and the
// spreadsheet list waiting for as long as the browser held the connection.
// These run the real client, connected, with fetch as the only fake and the
// clock mocked, so "fifteen seconds" is asserted exactly rather than waited.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../../api.js", import.meta.url), "utf8");
const anchor = 'import { API_URL, isConnected } from "./config.js";';
assert.equal(source.split(anchor).length, 2);
const api = await import("data:text/javascript;base64," + Buffer.from(
  source.replace(anchor, 'const API_URL = "https://api.example.invalid"; const isConnected = () => true;'),
).toString("base64"));

const abortError = () => Object.assign(new Error("The operation was aborted."), { name: "AbortError" });

/** A fetch that never answers, but rejects as a browser does when its signal aborts. */
function hangingFetch(calls = []) {
  return (url, options) => {
    calls.push({ url, options });
    return new Promise((_, reject) => {
      options.signal.addEventListener("abort", () => reject(abortError()), { once: true });
    });
  };
}

/** A response whose headers arrive and whose body never finishes, until aborted. */
function stalledBodyFetch() {
  return (url, options) => {
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('{"email":'));
        options.signal.addEventListener("abort", () => controller.error(abortError()), { once: true });
      },
    });
    return Promise.resolve(new Response(body, { status: 200, headers: { "Content-Type": "application/json" } }));
  };
}

async function withFetch(fake, run) {
  const prior = globalThis.fetch;
  globalThis.fetch = fake;
  try { await run(); } finally { globalThis.fetch = prior; }
}

/** Settle a promise's state without awaiting it to completion. */
function track(promise) {
  const state = { settled: false, error: null, value: undefined };
  promise.then((value) => { state.settled = true; state.value = value; }, (error) => { state.settled = true; state.error = error; });
  return state;
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

test("a request with no answer is abandoned at fifteen seconds, as TIMEOUT", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const calls = [];
  await withFetch(hangingFetch(calls), async () => {
    const state = track(api.fetchCollections());
    await flush();
    t.mock.timers.tick(api.REQUEST_TIMEOUT_MS - 1);
    await flush();
    assert.equal(state.settled, false, "still waiting one millisecond before the deadline");
    t.mock.timers.tick(1);
    await flush();
    assert.equal(state.settled, true);
    assert.equal(state.error.code, "TIMEOUT");
    assert.equal(state.error.status, 0);
    assert.equal(api.isUnreachable(state.error), true);
    assert.equal(calls[0].options.signal.aborted, true, "the stalled fetch itself is cancelled");
  });
  assert.equal(api.REQUEST_TIMEOUT_MS, 15_000);
});

test("the session check times out too, rather than reading as signed out", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  await withFetch(hangingFetch(), async () => {
    const state = track(api.fetchSession());
    await flush();
    t.mock.timers.tick(api.REQUEST_TIMEOUT_MS);
    await flush();
    assert.equal(state.error?.code, "TIMEOUT");
  });
});

test("a body that stalls after the headers is held to the same deadline", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  await withFetch(stalledBodyFetch(), async () => {
    const state = track(api.fetchArticle("a-brief"));
    await flush();
    await flush();
    assert.equal(state.settled, false);
    t.mock.timers.tick(api.REQUEST_TIMEOUT_MS);
    await flush();
    await flush();
    assert.equal(state.error?.code, "TIMEOUT");
  });
});

test("the caller's own abort is not a timeout, and reaches the fetch", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const calls = [];
  await withFetch(hangingFetch(calls), async () => {
    const controller = new AbortController();
    const state = track(api.fetchReleaseCollections({ signal: controller.signal }));
    await flush();
    controller.abort();
    await flush();
    assert.equal(calls[0].options.signal.aborted, true);
    assert.equal(state.error?.code, "NETWORK");
  });
});

test("Cedar and the research preview wait as long as the services behind them", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  await withFetch(hangingFetch(), async () => {
    const cedar = track(api.askCedar({ question: "What changed?" }));
    const research = track(api.fetchReleaseResearch("funding", "a".repeat(64)));
    await flush();
    t.mock.timers.tick(api.REQUEST_TIMEOUT_MS);
    await flush();
    assert.equal(cedar.settled, false, "Cedar's own deadline is 45 s; 15 s would abandon live answers");
    assert.equal(research.settled, false);
    t.mock.timers.tick(api.RESEARCH_TIMEOUT_MS - api.REQUEST_TIMEOUT_MS);
    await flush();
    assert.equal(research.error?.code, "TIMEOUT");
    assert.equal(cedar.settled, false);
    t.mock.timers.tick(api.CEDAR_TIMEOUT_MS - api.RESEARCH_TIMEOUT_MS);
    await flush();
    assert.equal(cedar.error?.code, "TIMEOUT");
  });
  assert.ok(api.CEDAR_TIMEOUT_MS > 45_000);
  assert.ok(api.RESEARCH_TIMEOUT_MS > 30_000);
});

test("an answer in time is returned, and its deadline is cleared", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const calls = [];
  const session = { email: "a@example.org", workspace_tier: "press" };
  await withFetch(async (url, options) => { calls.push(options); return Response.json(session); }, async () => {
    assert.deepEqual(await api.fetchSession(), session);
    t.mock.timers.tick(api.REQUEST_TIMEOUT_MS * 2);
    assert.equal(calls[0].signal.aborted, false, "no timer is left to abort a finished request");
  });
});

test("refusals keep their own code, and only no-answer reads as unreachable", async () => {
  await withFetch(async () => Response.json({ code: "NOT_INCLUDED", message: "Not on this plan." }, { status: 403 }), async () => {
    await assert.rejects(api.fetchReleaseCollections(), (error) => {
      assert.equal(error.code, "NOT_INCLUDED");
      assert.equal(api.isUnreachable(error), false);
      return true;
    });
  });
  await withFetch(async () => { throw new TypeError("Failed to fetch"); }, async () => {
    await assert.rejects(api.fetchReleaseCollections(), (error) => api.isUnreachable(error) && error.code === "NETWORK");
  });
  assert.equal(api.isUnreachable(null), false);
});
