/**
 * The Cedar panel is one panel on three surfaces, and the owner put two of
 * them side by side and saw the difference: Press's was wider than the
 * site's, and it said it answered from "prepared material". The geometry is
 * held to the site's measured numbers by the smoke suite in a browser; this
 * pins the two things a stylesheet and a component cannot report on their
 * own: that the rules still say what the browser test assumes they say, and
 * that both Press surfaces render the shared panel rather than a copy.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { EXPECTATION_LINE } from "./cedarConversation.js";
import { contextsFor, rulesFor } from "./cedarLauncherParity.test.js";

const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8");
/** The code without its comments: a phrase quoted in a note is not a phrase a reader sees. */
const code = (source) => source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const pressCss = () => read("../../styles/grove/press.css");
const door = () => read("../../pages/grove/PressDoorCedar.jsx");
const fab = () => read("../../pages/grove/PressCedarFab.jsx");
const panel = () => read("../../pages/grove/CedarPanel.jsx");

const topLevel = (needle) =>
  rulesFor(pressCss(), needle).filter((rule) => rule.selector === `.teim-rd ${needle}`);

test("the panel's desktop rule is the site's: 380px wide, the site's right offset, the site's ceiling", () => {
  const [rule] = topLevel(".cp-dc__panel");
  assert.ok(rule, "no top-level .cp-dc__panel rule");
  assert.match(rule.body, /width:\s*min\(380px,\s*calc\(100vw - 1\.8rem\)\)/);
  assert.match(rule.body, /right:\s*calc\(clamp\(0\.9rem,\s*2\.2vw,\s*1\.5rem\)/);
  assert.match(rule.body, /max-height:\s*calc\(100dvh - 5rem\)/);
});

test("the transcript is the site's transcript cap, as a height", () => {
  const [rule] = topLevel(".cp-dc__thread");
  assert.ok(rule);
  assert.match(rule.body, /(^|;|\s)height:\s*min\(400px,\s*52vh\)/);
  assert.match(rule.body, /flex:\s*1 1 auto/);
});

test("the phone keeps the whole screen", () => {
  const contexts = contextsFor(pressCss(), ".cp-dc__panel");
  assert.ok(contexts.some((c) => c.includes("max-width: 600px")), "no full-screen rule below 600px");
  const fullScreen = rulesFor(pressCss(), ".cp-dc__panel").find((r) => /inset:\s*0/.test(r.body));
  assert.ok(fullScreen, "the sub-600 rule no longer takes the screen");
});

test("both Press surfaces render the one shared panel", () => {
  for (const [name, source] of [["the door", door()], ["the reader", fab()]]) {
    assert.match(source, /<CedarPanel\b/, `${name} does not render CedarPanel`);
    assert.doesNotMatch(source, /cp-dc__disclaimer/, `${name} carries its own expectation line`);
    assert.doesNotMatch(code(source), /prepared material|prepared answers/, `${name} still announces its machinery`);
  }
  assert.match(panel(), /\{EXPECTATION_LINE\}/);
  assert.match(panel(), /cp-dc__followups/);
});

test("the door never imports the network", () => {
  assert.doesNotMatch(door(), /from "\.\.\/\.\.\/api/);
  assert.doesNotMatch(read("./doorCedar.js"), /fetch\(|from "\.\.\/\.\.\/api|from "\.\/api/);
  assert.doesNotMatch(read("./cedarConversation.js"), /fetch\(|from "\.\.\/\.\.\/api/);
});

test("the expectation line has no machinery in it", () => {
  assert.doesNotMatch(EXPECTATION_LINE, /prepared|does not query/);
});
