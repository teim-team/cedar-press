// Reading a published sample with a deadline, and noticing the connection
// coming back (sampleFetch.js). The hooks that use these keep only what
// arrived; a failure must surface as a throw, never as a value they store.
import assert from "node:assert/strict";
import test from "node:test";

import { createHash } from "node:crypto";

import { SAMPLE_TIMEOUT_MS, fetchSampleText, onBackOnline } from "./sampleFetch.js";

const digestOf = (text) => createHash("sha256").update(text, "utf8").digest("hex");
// Any well-formed digest: the timeout and status tests fail before it is read.
const ANY = "0".repeat(64);

const abortError = () => Object.assign(new Error("aborted"), { name: "AbortError" });
const flush = () => new Promise((resolve) => setImmediate(resolve));

test("a sample that never answers is abandoned at the deadline, and the fetch cancelled", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let signal;
  const fetchImpl = (path, options) => {
    signal = options.signal;
    return new Promise((_, reject) => options.signal.addEventListener("abort", () => reject(abortError())));
  };
  let outcome = null;
  fetchSampleText("/data/cedar/downloads/x.csv", { sha256: ANY, fetchImpl }).then(
    () => { outcome = "resolved"; },
    (error) => { outcome = error; },
  );
  await flush();
  t.mock.timers.tick(SAMPLE_TIMEOUT_MS - 1);
  await flush();
  assert.equal(outcome, null);
  t.mock.timers.tick(1);
  await flush();
  assert.match(outcome.message, /did not arrive within 15 seconds/);
  assert.equal(signal.aborted, true);
});

test("a body that stalls after the headers is held to the deadline too", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const fetchImpl = (path, options) => Promise.resolve(new Response(new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode("a,b\n"));
      options.signal.addEventListener("abort", () => controller.error(abortError()));
    },
  })));
  let outcome = null;
  fetchSampleText("/s.csv", { sha256: ANY, fetchImpl }).then(() => { outcome = "resolved"; }, (error) => { outcome = error; });
  await flush();
  t.mock.timers.tick(SAMPLE_TIMEOUT_MS);
  await flush();
  await flush();
  assert.ok(outcome instanceof Error, "rejected rather than resolved with a partial file");
});

test("a non-200 is a failure, thrown, not a value", async () => {
  await assert.rejects(
    fetchSampleText("/s.csv", { sha256: ANY, fetchImpl: async () => new Response("<html>", { status: 404 }) }),
    /answered 404/,
  );
  await assert.rejects(
    fetchSampleText("/s.csv", { sha256: ANY, fetchImpl: async () => { throw new TypeError("Failed to fetch"); } }),
    /Failed to fetch/,
  );
});

test("a sample in time is its text, with nothing left to abort it", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let signal;
  const text = await fetchSampleText("/s.csv", { sha256: digestOf("a,b\n1,2\n"), fetchImpl: async (path, options) => { signal = options.signal; return new Response("a,b\n1,2\n"); } });
  assert.equal(text, "a,b\n1,2\n");
  t.mock.timers.tick(SAMPLE_TIMEOUT_MS * 2);
  assert.equal(signal.aborted, false);
});

test("only bytes matching the published digest are a sample; nothing is fetched without one", async () => {
  let fetched = 0;
  const fetchImpl = async () => { fetched += 1; return new Response("record_type,record_key\nx,1\n"); };
  // The wrong bytes at the right path: a stale cache, or the raw preview.
  await assert.rejects(
    fetchSampleText("/data/cedar/downloads/need.csv", { sha256: digestOf("cedar_uid\nCE-1\n"), fetchImpl }),
    /digest mismatch/,
  );
  assert.equal(fetched, 1);
  // No digest, or a malformed one: refused before any request is made.
  for (const sha256 of [undefined, null, "", "abc", "G".repeat(64)]) {
    await assert.rejects(fetchSampleText("/data/cedar/downloads/need.csv", { sha256, fetchImpl }), /No published digest/);
  }
  assert.equal(fetched, 1);
});

test("onBackOnline calls back on each online event until unsubscribed", () => {
  const target = new EventTarget();
  let calls = 0;
  const stop = onBackOnline(() => { calls += 1; }, target);
  target.dispatchEvent(new Event("offline"));
  assert.equal(calls, 0);
  target.dispatchEvent(new Event("online"));
  target.dispatchEvent(new Event("online"));
  assert.equal(calls, 2);
  stop();
  target.dispatchEvent(new Event("online"));
  assert.equal(calls, 2);
  // No window in Node: a no-op rather than a throw.
  assert.doesNotThrow(() => onBackOnline(() => {}, undefined)());
});
