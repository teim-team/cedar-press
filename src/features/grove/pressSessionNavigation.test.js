import assert from "node:assert/strict";
import test from "node:test";
import {
  isWorkspaceHost,
  landingHref,
  loginRedirect,
  safeNext,
  workspaceSignInHref,
} from "./pressSessionNavigation.js";

test("public login goes to the workspace login page and nothing from the query rides along", () => {
  assert.equal(workspaceSignInHref(new URL("https://cedarpress.ai/?collection=deals&next=https://untrusted.invalid/")), "https://app.cedarpress.ai/login");
  assert.equal(workspaceSignInHref(new URL("https://www.cedarpress.ai/")), "https://app.cedarpress.ai/login");
});

test("workspace, preview and unrelated hosts never redirect their sign-in form", () => {
  for (const origin of ["https://app.cedarpress.ai", "http://localhost:5173", "https://example.org", "https://cedarpress.ai.attacker.invalid"]) {
    assert.equal(workspaceSignInHref(new URL(origin)), null);
  }
  assert.equal(workspaceSignInHref(null), null);
  assert.equal(workspaceSignInHref(new URL("http://cedarpress.ai")), null);
});

test("only the workspace host is the workspace", () => {
  assert.equal(isWorkspaceHost(new URL("https://app.cedarpress.ai/data")), true);
  for (const origin of ["https://cedarpress.ai", "https://www.cedarpress.ai", "https://app.cedarpress.ai.attacker.invalid"]) {
    assert.equal(isWorkspaceHost(new URL(origin)), false);
  }
});

test("the landing page leaves the workspace host, whose root is the login page", () => {
  assert.equal(landingHref(new URL("https://app.cedarpress.ai/login")), "https://cedarpress.ai/");
  for (const origin of ["https://cedarpress.ai", "http://localhost:5173", "https://d123.cloudfront.net"]) {
    assert.equal(landingHref(new URL(origin)), "/");
  }
});

test("next is a same-origin path or the root", () => {
  assert.equal(safeNext("/data?collection=deals"), "/data?collection=deals");
  for (const raw of [null, "", "data", "//untrusted.invalid", "/\\untrusted.invalid", "/\t/untrusted.invalid", "/\n/untrusted.invalid", "https://untrusted.invalid", "/login", "/login?next=/data"]) {
    assert.equal(safeNext(raw), "/");
  }
});

test("a signed-out visit to a deep link logs in first and comes back", () => {
  assert.equal(loginRedirect({ pathname: "/", search: "" }), "/login");
  assert.equal(loginRedirect({ pathname: "/data", search: "?collection=deals" }), "/login?next=%2Fdata%3Fcollection%3Ddeals");
  assert.equal(loginRedirect({ pathname: "/login", search: "" }), "/login");
});
