import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

// Execute the maintained client with its build-time configuration connected.
// Fetch is the sole fake; successful and failed HTTP response parsing is real.
const source = readFileSync(new URL("./api.js", import.meta.url), "utf8");
const anchor = 'import { API_URL, isConnected } from "./config.js";';
assert.equal(source.split(anchor).length, 2);
const api = await import("data:text/javascript;base64," + Buffer.from(
  source.replace(anchor, 'const API_URL = "https://api.example.invalid"; const isConnected = () => true;'),
).toString("base64"));

async function withResponse(response, run) {
  const prior = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return response; };
  try { await run(calls); } finally { globalThis.fetch = prior; }
}

test("an HTML200 login response reports failure instead of silently signing in nobody", async () => {
  await withResponse(new Response("<html>static app</html>", { status: 200, headers: { "Content-Type": "text/html" } }), async () => {
    await assert.rejects(api.login({ email: "a@example.org", password: "private" }), { code: "AUTH_RESPONSE_INVALID" });
  });
});

test("null, arrays and incomplete successful session payloads are refused", async () => {
  for (const value of [null, [], {}, { email: "a@example.org" }, { email: "", workspace_tier: "press" }, { email: "a@example.org", workspace_tier: {} }]) {
    await withResponse(Response.json(value), async () => {
      await assert.rejects(api.login({ email: "a@example.org", password: "private" }), { code: "AUTH_RESPONSE_INVALID" });
    });
  }
});

test("a valid server session keeps server permissions and sends cookie credentials", async () => {
  const session = { email: "a@example.org", workspace_tier: "press_pro", press: { canRead: true, shelfReach: "pro" } };
  await withResponse(Response.json(session), async (calls) => {
    assert.deepEqual(await api.login({ email: session.email, password: "private" }), session);
    assert.equal(calls[0].options.credentials, "include");
    assert.equal(calls[0].url, "https://api.example.invalid/auth/login");
    assert.equal(calls[0].options.method, "POST");
  });
});

test("session refresh distinguishes signed out from a misrouted successful response", async () => {
  await withResponse(Response.json({ code: "NOT_SIGNED_IN" }, { status: 401 }), async () => assert.equal(await api.fetchSession(), null));
  await withResponse(new Response("<html>wrong origin</html>"), async () => {
    await assert.rejects(api.fetchSession(), { code: "AUTH_RESPONSE_INVALID" });
  });
});

test("credential errors keep the server refusal", async () => {
  await withResponse(Response.json({ code: "INVALID_CREDENTIALS", message: "Sign-in failed." }, { status: 401 }), async () => {
    await assert.rejects(api.login({ email: "a@example.org", password: "wrong" }), { code: "INVALID_CREDENTIALS", status: 401 });
  });
});

test("activation refuses a misrouted success and keeps a genuine session payload", async () => {
  const body = { code: "ABCD1234", email: "existing@example.org", password: "not-a-live-password" };
  await withResponse(new Response("<html>static app</html>"), async () => {
    await assert.rejects(api.activatePressAccount(body), { code: "AUTH_RESPONSE_INVALID" });
  });
  const session = { email: body.email, workspace_tier: "press" };
  await withResponse(Response.json(session), async () => {
    assert.deepEqual(await api.activatePressAccount(body), session);
  });
});
