/**
 * The Cedar launcher is one control with three implementations, and it has
 * already drifted once: the in-app launcher collapsed to an anonymous circle
 * that said its name only on hover, so a phone — having no hover — never saw
 * it at all, while the door two thousand lines away and teim-app both went on
 * showing "Ask Cedar" at rest.
 *
 * Nothing failed when that happened. It is a stylesheet, and a stylesheet has
 * no other way to tell anyone. So the parity is asserted here instead, on the
 * two properties that actually broke: the name is present in the markup at
 * every width, and the resting shape is not collapsed away behind a hover
 * that touch devices do not have.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8");

const inAppFab = () => read("../../pages/grove/PressCedarFab.jsx");
const doorFab = () => read("../../pages/grove/PressDoorCedar.jsx");
const pressCss = () => read("../../styles/grove/press.css");

/**
 * The `.teim-rd`-scoped rules whose selector mentions `needle`, with comments
 * stripped first — a rule quoted inside a comment is prose, not a rule, and
 * matching it is how a guard starts passing on the strength of its own
 * documentation.
 */
export function rulesFor(css, needle) {
  const code = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const rules = [];
  const re = /([^{}]+)\{([^{}]*)\}/g;
  let m;
  while ((m = re.exec(code)) !== null) {
    const selector = m[1].trim();
    if (selector.startsWith("@")) continue;
    if (selector.includes(needle)) rules.push({ selector, body: m[2].trim() });
  }
  return rules;
}

/** The media queries a selector's rules appear inside, `""` for top level. */
export function contextsFor(css, needle) {
  const code = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const contexts = new Set();
  const stack = [];
  const token = /(@[^{]*)\{|([^{}]+)\{|\}/g;
  let m;
  while ((m = token.exec(code)) !== null) {
    if (m[0] === "}") {
      stack.pop();
      continue;
    }
    if (m[1] !== undefined) {
      stack.push(m[1].trim());
      continue;
    }
    const selector = m[2].trim();
    if (selector.includes(needle)) contexts.add(stack.join(" ").trim());
    stack.push(selector);
  }
  return [...contexts];
}

test("every Cedar launcher says its name in the markup", () => {
  for (const [name, source] of [
    ["the in-app launcher", inAppFab()],
    ["the door launcher", doorFab()],
  ]) {
    assert.match(
      source,
      /Ask Cedar/,
      `${name} must carry the words "Ask Cedar" as text, not only as an aria-label`,
    );
  }
});

test("the in-app launcher carries the same two lines as the door", () => {
  const source = inAppFab();
  assert.match(source, /cedar-widget__launcher-label">Ask Cedar</);
  assert.match(source, /cedar-widget__launcher-context">Cedar Press</);

  const door = doorFab();
  assert.match(door, /<b>Ask Cedar<\/b>/);
  assert.match(door, /<small>Cedar Press<\/small>/);
});

test("the in-app launcher is not collapsed to a fixed square at rest", () => {
  // A circle was width+height+border-radius:50% on the launcher itself. The
  // pill takes its size from its padding and its content, so any rule that
  // pins BOTH dimensions is the collapse coming back.
  const collapsed = rulesFor(pressCss(), ".cedar-widget__launcher").filter(
    (rule) =>
      !rule.selector.includes(":hover") &&
      !rule.selector.includes(":focus") &&
      /(^|;|\s)width\s*:/.test(rule.body) &&
      /(^|;|\s)height\s*:/.test(rule.body),
  );
  assert.deepEqual(
    collapsed.map((rule) => rule.selector),
    [],
    "the resting launcher must not pin width and height; that is the circle",
  );
});

test("the launcher's name is never hidden behind a hover", () => {
  // `max-width: 0` / `opacity: 0` on the copy was how the name was clipped,
  // and it was un-clipped only inside `@media (hover: hover)` — which is
  // exactly the query a phone fails.
  for (const rule of rulesFor(pressCss(), ".cedar-widget__launcher-copy")) {
    assert.doesNotMatch(
      rule.body,
      /max-width\s*:\s*0|opacity\s*:\s*0(\D|$)/,
      `"${rule.selector}" clips the launcher's name away from touch devices`,
    );
  }
  for (const rule of rulesFor(pressCss(), ".cedar-widget__launcher-context")) {
    assert.doesNotMatch(
      rule.body,
      /display\s*:\s*none/,
      `"${rule.selector}" drops the launcher's second line`,
    );
  }
});

test("the launcher clears the phone's home indicator", () => {
  const anchors = rulesFor(pressCss(), ".cedar-widget").filter(
    (rule) => /^\.teim-rd \.cedar-widget$/.test(rule.selector) && /position\s*:\s*fixed/.test(rule.body),
  );
  assert.equal(anchors.length, 1, "expected exactly one fixed anchor for the widget");
  assert.match(
    anchors[0].body,
    /bottom\s*:\s*calc\([^)]*safe-area-inset-bottom/,
    "a bottom-anchored launcher must account for the iOS home indicator",
  );
});

/* ---------- the readers, pinned against their own blind spots ---------- */

test("rulesFor ignores selectors quoted inside comments", () => {
  const css = `/* .teim-rd .cedar-widget__launcher { width: 3rem; height: 3rem; } */
.teim-rd .cedar-widget__launcher { padding: 0.75rem 1.25rem; }`;
  const rules = rulesFor(css, ".cedar-widget__launcher");
  assert.equal(rules.length, 1);
  assert.equal(rules[0].body, "padding: 0.75rem 1.25rem;");
});

test("rulesFor reads a rule nested inside a media query", () => {
  const css = `@media (hover: hover) {
  .teim-rd .cedar-widget__launcher:hover { width: auto; height: auto; }
}`;
  const rules = rulesFor(css, ".cedar-widget__launcher");
  assert.equal(rules.length, 1);
  assert.match(rules[0].selector, /:hover$/);
});

test("contextsFor names the media query a rule sits in", () => {
  const css = `.teim-rd .cedar-widget__launcher { padding: 1rem; }
@media (max-width: 640px) {
  .teim-rd .cedar-widget__launcher { padding: 0.5rem; }
}`;
  const contexts = contextsFor(css, ".cedar-widget__launcher");
  assert.ok(contexts.includes(""), "expected a top-level rule");
  assert.ok(
    contexts.some((context) => context.includes("max-width: 640px")),
    "expected the phone rule to be attributed to its media query",
  );
});

test("the collapse guard would have caught the rule it replaced", () => {
  const css = `.teim-rd .cedar-widget__launcher { padding: 0; width: 3.25rem; height: 3.25rem; border-radius: 50%; }`;
  const collapsed = rulesFor(css, ".cedar-widget__launcher").filter(
    (rule) =>
      !rule.selector.includes(":hover") &&
      !rule.selector.includes(":focus") &&
      /(^|;|\s)width\s*:/.test(rule.body) &&
      /(^|;|\s)height\s*:/.test(rule.body),
  );
  assert.equal(collapsed.length, 1, "the real historical rule must trip this guard");
});

test("the clipping guard would have caught the rule it replaced", () => {
  const css = `.teim-rd .cedar-widget__launcher-copy { max-width: 0; opacity: 0; overflow: hidden; }`;
  const [rule] = rulesFor(css, ".cedar-widget__launcher-copy");
  assert.match(rule.body, /max-width\s*:\s*0|opacity\s*:\s*0(\D|$)/);
});
