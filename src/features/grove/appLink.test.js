// Where Press sends a reader who wants Cedar Grove.
//
// Press and Grove share the data and nothing else a reader can use: a Press
// subscriber has no Grove account to land in. So a Grove link goes to the
// product's page on lumecon.ai, and only the platform links ("Open the
// platform"), which do lead to an account the reader holds, stay on the app
// origin. The source scan below is the claim that matters: it reads the
// pages, so a Grove link that quietly goes back to an app route fails here
// rather than in a reader's browser.

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import test from "node:test";

import { GROVE_MARKETING_URL, appUrl } from "./appLink.js";

const PAGES = new URL("../../pages/grove/", import.meta.url);

function pageSources() {
  return readdirSync(PAGES)
    .filter((name) => /\.jsx?$/.test(name) && !/\.test\./.test(name))
    .map((name) => [name, readFileSync(new URL(name, PAGES), "utf8")]);
}

test("the Grove link is the marketing page, and not an app route", () => {
  assert.equal(GROVE_MARKETING_URL, "https://lumecon.ai/cedar-grove");
  assert.doesNotMatch(GROVE_MARKETING_URL, /\/app(\/|$)/);
  assert.notEqual(GROVE_MARKETING_URL, appUrl("/app/grove"));
});

test("no page links Cedar Grove into the app", () => {
  for (const [name, source] of pageSources()) {
    assert.doesNotMatch(source, /appUrl\(\s*["'`]\/app\/grove/, `${name} sends Grove into the app`);
  }
});

test("every Grove call to action opens the marketing page in a new tab", () => {
  const found = [];
  for (const [name, source] of pageSources()) {
    for (const match of source.matchAll(/<a\b([^>]*)>\s*(?:Open|Explore) Cedar Grove\b/g)) {
      found.push({ name, attrs: match[1] });
    }
  }
  assert.ok(found.length >= 2, `expected the shelf and the closing statement to link Grove, found ${found.length}`);
  for (const { name, attrs } of found) {
    assert.match(attrs, /href=\{GROVE_MARKETING_URL\}/, `${name}: ${attrs}`);
    assert.match(attrs, /target="_blank"/, name);
    assert.match(attrs, /rel="noreferrer"/, name);
  }
});

test("the platform link is still the app", () => {
  const fab = readFileSync(new URL("PressCedarFab.jsx", PAGES), "utf8");
  assert.match(fab, /href=\{appUrl\("\/app"\)\}[^>]*>Open the platform/);
  assert.match(appUrl("/app"), /\/app$/);
});
