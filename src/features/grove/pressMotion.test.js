/**
 * The motion contract (docs/DESIGN_SYSTEM.md, "Motion"), pinned where a
 * stylesheet cannot report on itself.
 *
 * The smoke suite measures the behaviour in a browser: a tile lifts under a
 * fine pointer and not under a finger, the twelve arrive in order, reduced
 * motion is immediate. This holds the RULES to what those tests assume, so a
 * rule moved out of its media query or onto a second curve fails here in
 * milliseconds rather than in a browser run somebody skipped.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { contextsFor, rulesFor } from "./cedarLauncherParity.test.js";

const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8");
const pressCss = () => read("../../styles/grove/press.css");
const uncommented = (css) => css.replace(/\/\*[\s\S]*?\*\//g, "");

/** The family's curve: lumecon-website `global.css` `--ease`, and the page entrance here. */
const THE_CURVE = "cubic-bezier(0.22, 1, 0.36, 1)";
const FINE_POINTER = "@media (hover: hover) and (pointer: fine)";
const REDUCED = "@media (prefers-reduced-motion: reduce)";

/** Every pointer response the pass added or touched. A finger gets none of them. */
const HOVER_RULES = [
  ".cp-dcol__tile:hover",
  ".cp-why__item:hover",
  ".cp-ways__row:hover",
  ".cp-hero3__stage:hover",
  ".cp-hero3__run li:hover",
  ".cp-proc:hover",
  ".cp-proc__stage:hover",
];

test("the curve is declared once, on the root, and the door aliases it", () => {
  const css = uncommented(pressCss());
  const declarations = css.match(/--cp-ease:\s*[^;]+;/g) ?? [];
  assert.deepEqual(declarations, [`--cp-ease: ${THE_CURVE};`], "one declaration, the family's curve");
  const [root] = rulesFor(css, ".teim-rd").filter((r) => r.selector === ".teim-rd" && r.body.includes("--cp-ease"));
  assert.ok(root, "--cp-ease is declared on .teim-rd, where every page can read it");
  const door = rulesFor(css, ".cp-door").find((r) => r.selector === ".teim-rd .cp-door");
  assert.match(door.body, /--door-ease:\s*var\(--cp-ease\)/, "the door's own ease is the alias, not a second copy");
});

test("every hover the pass touched lives only under the fine-pointer query", () => {
  const css = pressCss();
  for (const needle of HOVER_RULES) {
    const contexts = contextsFor(css, needle);
    assert.ok(contexts.length, `${needle} has no rule at all`);
    for (const context of contexts) {
      assert.ok(
        context.startsWith(FINE_POINTER) || context.startsWith(REDUCED),
        `${needle} is reachable by a finger: found under "${context || "top level"}"`,
      );
    }
    assert.ok(contexts.some((c) => c.startsWith(FINE_POINTER)), `${needle} never answers a fine pointer`);
  }
});

test("keyboard focus lifts a tile the way a pointer does", () => {
  const [rule] = rulesFor(pressCss(), ".cp-dcol__tile:focus-visible");
  assert.ok(rule);
  assert.match(rule.body, /transform:\s*translateY\(-2px\)/);
  assert.match(rule.body, /outline:\s*2px solid/);
});

test("the arrivals run on the curve, hold their start, and are exempt on the first screen", () => {
  const css = pressCss();
  for (const [needle, keyframe] of [
    [".cp-dcol__grid > li", "cp-tile-in"],
    [".cp-proc__stage", "cp-stage-in"],
  ]) {
    const arrival = rulesFor(css, needle).find((r) => r.body.includes(`animation: ${keyframe}`));
    assert.ok(arrival, `${needle} has no ${keyframe} arrival`);
    assert.match(arrival.selector, /\.cp-fade\.is-in:not\(\.cp-fade--now\)/, "only once the block is in, never on the first screen");
    assert.match(arrival.body, new RegExp(`animation: ${keyframe} [\\d.]+s var\\(--cp-ease\\) backwards`), "the curve, and a backwards fill only");
    assert.match(arrival.body, /animation-delay:\s*calc\(var\(--i, 0\) \* \d+ms\)/, "staggered on the element's own index");
    assert.doesNotMatch(arrival.body, /forwards|both/, "a forward fill would pin the element and defeat its hover");
    assert.match(uncommented(css), new RegExp(`@keyframes ${keyframe} \\{ from \\{ opacity: 0; transform: translateY\\(\\d+px\\); \\} \\}`));
    const stilled = contextsFor(css, needle).some((c) => c.startsWith(REDUCED));
    assert.ok(stilled, `${needle} is not stilled under reduced motion`);
  }
});

test("the components write the index the stylesheet staggers on", () => {
  assert.match(read("../../pages/grove/PressDoorCollections.jsx"), /<li key=\{entry\.id\} style=\{\{ "--i": i \}\}>/);
  assert.match(read("../../pages/grove/pressMethodSections.jsx"), /className="cp-proc__stage" key=\{stage\.id\} style=\{\{ "--i": index \}\}/);
  assert.match(read("../../pages/grove/PressDoorCollections.jsx"), /cp-dcol__shelf\$\{active\?\.shelf === tier\.shelf \? " is-active" : ""\}/);
});

test("the shelf band's active state is a colour, not a movement", () => {
  const css = pressCss();
  const active = rulesFor(css, ".cp-dcol__shelf.is-active");
  assert.ok(active.length >= 2);
  for (const rule of active) {
    assert.doesNotMatch(rule.body, /transform|animation|box-shadow/, `${rule.selector} moves`);
    assert.match(rule.body, /color/);
  }
  for (const needle of [".cp-dcol__shelf {", ".cp-dcol__tier {"]) {
    const rule = rulesFor(css, needle.slice(0, -2)).find((r) => r.selector === `.teim-rd ${needle.slice(0, -2)}` && /transition/.test(r.body));
    assert.ok(rule, `${needle} has no transition`);
    assert.match(rule.body, /var\(--cp-ease\)/, `${needle} eases on something other than the curve`);
  }
});

test("nothing the pass added names a second curve", () => {
  // The rules this pass wrote all say var(--cp-ease). Pre-existing rules on
  // other curves are recorded as drift in docs/DESIGN_SYSTEM.md, not fixed here.
  const css = uncommented(pressCss());
  for (const needle of [".cp-dcol.cp-fade.is-in", ".cp-ch.cp-fade.is-in", ".cp-dcol__shelf", ".cp-dcol__tier", ".cp-proc__stage {", ".cp-proc__name {"]) {
    for (const rule of rulesFor(css, needle.replace(" {", ""))) {
      if (!/transition|animation/.test(rule.body)) continue;
      const literal = rule.body.replace(/var\(--cp-ease\)/g, "");
      assert.doesNotMatch(literal, /cubic-bezier|\bease\b/, `${rule.selector} names a curve instead of the token`);
    }
  }
});
