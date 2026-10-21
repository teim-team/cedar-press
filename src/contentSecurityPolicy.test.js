// The page's content policy must let the Datadog SDK reach its intake (F-42).
// The SDK sends to browser-intake-<site>, built by its own buildEndpointUrl,
// which is not a subdomain of the site: a policy allowing https://*.datadoghq.com
// blocked every send while looking right. This asks the installed SDK for the
// host, so an upgrade that changes it, or a new default site, fails here rather
// than in a subscriber's browser.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildEndpointUrl } from "@datadog/js-core/transport";
import { DATADOG } from "./config.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const policy = html.match(/http-equiv="Content-Security-Policy"\s+content="([^"]*)"/)?.[1];
const connectSrc = policy
  ?.split(";")
  .map((directive) => directive.trim().split(/\s+/))
  .find(([name]) => name === "connect-src")
  ?.slice(1);

// The default site, and the EU site the policy has allowed since it was written.
const SITES = [DATADOG.site, "datadoghq.eu"];
const intake = (site) => new URL(buildEndpointUrl({ site, path: "/api/v2/rum" })).origin;

test("the policy has a connect-src", () => {
  assert.ok(connectSrc?.length, "no connect-src in index.html's Content-Security-Policy");
});

test("connect-src allows the intake host the SDK sends to for each supported site", () => {
  for (const site of SITES) {
    assert.ok(connectSrc.includes(intake(site)), `${site}: ${intake(site)} is not in connect-src`);
  }
});

test("every Datadog entry in connect-src is an intake host the SDK sends to", () => {
  const allowed = new Set(SITES.map(intake));
  for (const source of connectSrc.filter((entry) => /datadog/i.test(entry))) {
    assert.ok(allowed.has(source), `${source} is not a host the Datadog SDK sends to`);
  }
});
