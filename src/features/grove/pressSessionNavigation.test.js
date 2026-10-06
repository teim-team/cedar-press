import assert from "node:assert/strict";
import test from "node:test";
import { requestedSignIn, workspaceSignInHref } from "./pressSessionNavigation.js";

test("public login goes to the canonical workspace and preserves only a valid collection", () => {
  const href = workspaceSignInHref(new URL("https://cedarpress.ai/?collection=deals&next=https://untrusted.invalid/"));
  assert.equal(href, "https://app.cedarpress.ai/?signin=1&collection=deals");
  assert.equal(workspaceSignInHref(new URL("https://www.cedarpress.ai/")), "https://app.cedarpress.ai/?signin=1");
});

test("workspace, preview and unrelated hosts never redirect their sign-in form", () => {
  for (const origin of ["https://app.cedarpress.ai", "http://localhost:5173", "https://example.org", "https://cedarpress.ai.attacker.invalid"]) {
    assert.equal(workspaceSignInHref(new URL(origin)), null);
  }
  assert.equal(workspaceSignInHref(null), null);
  assert.equal(workspaceSignInHref(new URL("http://cedarpress.ai")), null);
});

test("untrusted collection values cannot change the workspace destination", () => {
  assert.equal(workspaceSignInHref(new URL("https://cedarpress.ai/?collection=//untrusted.invalid")), "https://app.cedarpress.ai/?signin=1");
});

test("only an explicit sign-in link opens the form on arrival", () => {
  assert.equal(requestedSignIn("?signin=1&collection=deals"), true);
  for (const search of ["", "?signin=true", "?signin=0", "?next=signin%3D1"]) assert.equal(requestedSignIn(search), false);
});
