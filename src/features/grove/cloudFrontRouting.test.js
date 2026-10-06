import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../../../infrastructure/cedarpress-router.js", import.meta.url), "utf8");
const handler = vm.runInNewContext(source + "\nhandler;", {}, { timeout: 1000 });
function event(host, uri, querystring = {}) {
  return { request: { method: "GET", uri, querystring, headers: { host: { value: host } } } };
}

test("workspace login and all registered app route families serve the app shell without redirect", () => {
  for (const uri of ["/", "/data", "/settings/", "/methods", "/whats-new", "/priorities", "/record",
    "/articles", "/articles/research-note", "/entity/CE-000001", "/research-access", "/tribal-data-request"]) {
    const input = event("app.cedarpress.ai", uri, { signin: { value: "1" } });
    const result = handler(input);
    assert.equal(result, input.request);
    assert.equal(result.uri, "/404.html", uri);
    assert.equal(result.statusCode, undefined);
    assert.deepEqual(result.querystring, { signin: { value: "1" } });
  }
});

test("workspace assets and unknown paths remain exact requests", () => {
  for (const uri of ["/assets/index-abcdef.js", "/data/cedar/manifest.json", "/data/cedar/samples/deals/spreadsheet__10.csv",
    "/robots.txt", "/missing-page", "/entity", "/articles/example/extra", "/data//"]) {
    assert.equal(handler(event("app.cedarpress.ai", uri)).uri, uri);
  }
});

test("the public site's prerendered pages and hashed assets keep their existing mapping", () => {
  for (const [uri, expected] of [["/", "/index.html"], ["/tribal-data-request", "/tribal-data-request/index.html"],
    ["/research-access/", "/research-access/index.html"], ["/assets/app.js", "/assets/app.js"]]) {
    assert.equal(handler(event("cedarpress.ai", uri)).uri, expected);
  }
});

test("www canonical redirect preserves encoded and repeated query values", () => {
  const result = handler(event("www.cedarpress.ai", "/record", {
    k: { value: "deals" }, r: { value: "ACQ%2F2025" }, from: { value: "q%3DNative%2BLand%26year%3D2025" },
    tag: { value: "one", multiValue: [{ value: "one" }, { value: "two" }] },
  }));
  assert.equal(result.statusCode, 301);
  assert.equal(result.headers.location.value,
    "https://cedarpress.ai/record?k=deals&r=ACQ%2F2025&from=q%3DNative%2BLand%26year%3D2025&tag=one&tag=two");
});

test("API and authentication paths cannot become successful static app documents", () => {
  for (const host of ["cedarpress.ai", "app.cedarpress.ai"]) {
    for (const uri of ["/me", "/me/", "/auth/login", "/auth/logout", "/press/activation", "/press/profile", "/api/health"]) {
      const input = event(host, uri);
      assert.equal(handler(input).uri, uri);
    }
  }
});

test("HEAD requests retain their method and known routes use the existing build shell", () => {
  const input = event("app.cedarpress.ai", "/record");
  input.request.method = "HEAD";
  assert.equal(handler(input).method, "HEAD");
  const pkg = JSON.parse(readFileSync(new URL("../../../package.json", import.meta.url), "utf8"));
  assert.match(pkg.scripts.build, /cp dist-site\/index\.html dist-site\/404\.html/);
});
