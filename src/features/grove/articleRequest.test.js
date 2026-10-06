import assert from "node:assert/strict";
import test from "node:test";
import { startArticleRequest, visibleArticleState } from "./articleRequest.js";

const tick = () => new Promise((resolve) => setImmediate(resolve));

test("logout aborts and suppresses a late successful body response", async () => {
  let resolveRequest;
  let signal;
  const results = [];
  const stop = startArticleRequest((options) => {
    signal = options.signal;
    return new Promise((resolve) => { resolveRequest = resolve; });
  }, (state) => results.push(state));
  await tick();
  stop();
  assert.equal(signal.aborted, true);
  resolveRequest({ article: { body: ["private"] } });
  await tick();
  assert.deepEqual(results, []);
});

test("changing owners hides old content before the next request resolves", () => {
  const one = { email: "same@example.org" };
  const two = { email: "same@example.org" };
  const state = { owner: one, status: "ready", data: { body: ["private"] } };
  assert.equal(visibleArticleState(state, one, true), state);
  assert.equal(visibleArticleState(state, two, true).data, null);
  assert.equal(visibleArticleState(state, one, false).data, null);
});

test("successful responses and actual absence have distinct states", async () => {
  const results = [];
  startArticleRequest(async () => ({ articles: [] }), (state) => results.push(state));
  await tick();
  assert.deepEqual(results, [{ status: "ready", data: { articles: [] } }]);
  startArticleRequest(async () => { throw { status: 404 }; }, (state) => results.push(state));
  await tick();
  assert.equal(results[1].status, "not-found");
});

test("an unavailable API gives no static subscriber content", async () => {
  const results = [];
  startArticleRequest(async () => { throw new Error("Offline"); }, (state) => results.push(state));
  await tick();
  assert.deepEqual(results, [{ status: "unavailable", data: null }]);
});
