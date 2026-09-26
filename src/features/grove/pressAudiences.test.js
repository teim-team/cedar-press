/**
 * The door's use-case band: the gate between released and announced
 * collections, the switch from interim copy to the owner's launch copy, and
 * the rotation rules.
 *
 * The smoke suite renders the band; this holds the rules it renders from, in
 * milliseconds, including the one thing it must never do: resolve an id that
 * no current release carries.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { PRESS_CATALOG, STOREFRONT_CATALOG } from "./pressCatalog.js";
import {
  ANNOUNCED_COLLECTIONS,
  ANNOUNCED_IDS,
  isAnnounced,
  liveCollection,
  liveIdsOf,
} from "./pressAnnounced.js";
import {
  INITIAL_ROTATION,
  MIN_COLLECTIONS,
  PRESS_AUDIENCES,
  ROTATE_MS,
  citedIds,
  counterLabel,
  isCitable,
  resolveAudience,
  rotationReducer,
  shouldRotate,
  uncoveredIds,
  visibleAudiences,
} from "./pressAudiences.js";

const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8");

/** The catalog as it would stand once the announced collections launch. */
const launched = (ids = ANNOUNCED_IDS) => [
  ...STOREFRONT_CATALOG,
  ...ANNOUNCED_COLLECTIONS.filter((entry) => ids.includes(entry.id)).map((entry) => ({
    ...entry,
    shelf: "pro",
  })),
];

/** Words a sentence may not use while the giving and parcel collections are gated. */
const GATED_SUBJECT = /parcel|property|philanthrop|private giving|foundation/i;

// ── The gate ──────────────────────────────────────────────────────────────

test("the announced collections are declared once, and are not in the catalog", () => {
  assert.deepEqual([...ANNOUNCED_IDS].sort(), ["foundation-corporate-giving", "plot"]);
  const catalogIds = new Set(PRESS_CATALOG.map((entry) => entry.id));
  for (const id of ANNOUNCED_IDS) {
    assert.ok(!catalogIds.has(id), `${id} is both announced and in the catalog: move it, do not copy it`);
  }
  for (const entry of ANNOUNCED_COLLECTIONS) {
    assert.ok(entry.name && entry.short && entry.blurb && entry.icon, entry.id);
  }
});

test("the public resolver never returns an announced collection", () => {
  for (const id of ANNOUNCED_IDS) {
    assert.equal(liveCollection(id), null, id);
    assert.ok(!liveIdsOf().has(id), id);
    assert.ok(isAnnounced(id));
  }
  assert.equal(liveCollection("funding")?.id, "funding");
  assert.equal(isAnnounced("funding"), false);
});

test("every collection an audience cites is live or deliberately gated", () => {
  for (const id of citedIds()) {
    assert.ok(isCitable(id), `${id} is neither in the catalog nor announced`);
  }
  assert.equal(isCitable("gaming"), false, "an id nobody declared is refused");
});

test("today, no shown audience cites a gated collection or talks about one", () => {
  const shown = visibleAudiences();
  assert.ok(shown.length);
  for (const audience of shown) {
    for (const entry of audience.collections) {
      assert.ok(entry, `${audience.id} resolved a missing collection`);
      assert.ok(!isAnnounced(entry.id), `${audience.id} shows ${entry.id}`);
    }
    if (audience.version === "now") {
      assert.doesNotMatch(audience.use, GATED_SUBJECT, `${audience.id}'s interim copy names a gated subject`);
    }
    assert.ok(audience.collections.length >= MIN_COLLECTIONS, `${audience.id} is too thin to show`);
  }
});

test("every interim sentence cites live collections only and names no gated subject", () => {
  const gated = new Set(ANNOUNCED_IDS);
  for (const audience of PRESS_AUDIENCES) {
    if (!audience.now) continue;
    for (const id of audience.now.collections) assert.ok(!gated.has(id), `${audience.id} now cites ${id}`);
    assert.doesNotMatch(audience.now.use, GATED_SUBJECT, audience.id);
  }
});

test("an audience that exists only for a gated collection is hidden until launch", () => {
  const ids = visibleAudiences().map((audience) => audience.id);
  assert.ok(!ids.includes("foundations-philanthropy"));
  assert.equal(ids.length, PRESS_AUDIENCES.length - 1);
  assert.equal(resolveAudience(PRESS_AUDIENCES.find((a) => a.id === "foundations-philanthropy")), null);
});

test("an audience with fewer than three live collections is hidden rather than shown thin", () => {
  const thin = { id: "thin", label: "Thin", atLaunch: { use: "x", collections: ["funding", "deals"] }, now: null };
  assert.equal(resolveAudience(thin), null);
});

// ── Flipping the gate ─────────────────────────────────────────────────────

test("launching both collections switches every audience to the owner's copy", () => {
  const catalog = launched();
  const shown = visibleAudiences(catalog);
  assert.equal(shown.length, PRESS_AUDIENCES.length, "all ten, Foundations included");
  for (const audience of shown) {
    const declared = PRESS_AUDIENCES.find((a) => a.id === audience.id);
    assert.equal(audience.version, "atLaunch", audience.id);
    assert.equal(audience.use, declared.atLaunch.use, audience.id);
    assert.deepEqual(audience.collections.map((entry) => entry.id), [...declared.atLaunch.collections]);
  }
  assert.equal(counterLabel(0, shown.length), "01 / 10");
});

test("launching one collection switches only the audiences that cite nothing else gated", () => {
  const catalog = launched(["plot"]);
  const byId = Object.fromEntries(visibleAudiences(catalog).map((a) => [a.id, a]));
  // Cites PLOT and nothing else gated: the owner's copy.
  assert.equal(byId["ancs-nhos"].version, "atLaunch");
  assert.equal(byId["banks-lenders"].version, "atLaunch");
  assert.equal(byId.advisors.version, "atLaunch");
  // Also cites the giving collection: still interim.
  assert.equal(byId["tribal-nations"].version, "now");
  assert.equal(byId.journalists.version, "now");
  assert.equal(byId["foundations-philanthropy"], undefined);
});

test("where the owner's sentence cites only live collections, it is the copy today", () => {
  const byId = Object.fromEntries(visibleAudiences().map((a) => [a.id, a]));
  for (const id of ["native-enterprises", "businesses", "universities-researchers"]) {
    assert.equal(byId[id].version, "atLaunch", id);
  }
});

// ── Coverage: the band is the way from a task to every collection ─────────

test("every live collection is cited by at least one shown use case", () => {
  assert.deepEqual(uncoveredIds(), [], "a live collection no use case leads to");
  assert.equal(STOREFRONT_CATALOG.length, 12);
});

test("with the gate open, all fourteen are still covered", () => {
  const catalog = launched();
  assert.equal(catalog.length, 14);
  assert.deepEqual(uncoveredIds(catalog), []);
  for (const id of ANNOUNCED_IDS) {
    assert.ok(
      visibleAudiences(catalog).some((audience) => audience.collections.some((entry) => entry.id === id)),
      `${id} launches with no use case citing it`,
    );
  }
});

test("coverage fails loudly when a collection loses its last use case", () => {
  const withoutNagpra = PRESS_AUDIENCES.map((audience) => ({
    ...audience,
    atLaunch: audience.atLaunch && {
      ...audience.atLaunch,
      collections: audience.atLaunch.collections.map((id) => (id === "nagpra" ? "funding" : id)),
    },
  }));
  assert.deepEqual(uncoveredIds(STOREFRONT_CATALOG, withoutNagpra), ["nagpra"]);
});

// ── Copy and data rules ───────────────────────────────────────────────────

test("labels and sentences keep the house style", () => {
  for (const audience of PRESS_AUDIENCES) {
    assert.doesNotMatch(audience.label, /&/, `${audience.id}: "and", never an ampersand`);
    for (const version of [audience.atLaunch, audience.now]) {
      if (!version) continue;
      assert.doesNotMatch(version.use, /[—&]/, `${audience.id}: no em dash, no ampersand`);
      assert.doesNotMatch(version.use, /\bimpact\b/i, `${audience.id}: "contribution", not "impact"`);
      assert.match(version.use, /^[A-Z].*\.$/, `${audience.id}: a complete sentence`);
      assert.ok(version.collections.length >= MIN_COLLECTIONS && version.collections.length <= 5, audience.id);
    }
  }
});

test("the band names collections by id only: no second catalog", () => {
  const catalogIds = new Set(PRESS_CATALOG.map((entry) => entry.id));
  for (const id of citedIds()) assert.ok(catalogIds.has(id) || isAnnounced(id), id);
  // Neither module restates a collection's display name; names come from the catalog.
  for (const file of ["./pressAudiences.js", "./pressAnnounced.js"]) {
    const src = read(file);
    assert.doesNotMatch(src, /\bshort:\s*"(?!PLOT"|Foundation & Corporate Giving")/, `${file} defines a collection`);
    for (const entry of PRESS_CATALOG) {
      assert.ok(!src.includes(`name: "${entry.name}"`), `${file} restates ${entry.id}`);
    }
  }
});

test("both new marks are keyed in the icon family, as is every live collection", () => {
  const icons = read("../../pages/grove/pressCollectionIcons.jsx");
  const block = icons.slice(icons.indexOf("export const COLLECTION_ICONS"));
  const keyed = (id) => new RegExp(`(^|\\s)(${id}|"${id}"):\\s*\\w+Icon,`, "m").test(block);
  for (const entry of ANNOUNCED_COLLECTIONS) assert.ok(keyed(entry.icon), `no mark for ${entry.id}`);
  for (const entry of STOREFRONT_CATALOG) assert.ok(keyed(entry.id), `no mark for ${entry.id}`);
  // Same family: the shared glyph props, no fills, no gradients.
  for (const name of ["GivingIcon", "PlotIcon"]) {
    const start = icons.indexOf(`const ${name} = (`);
    const body = icons.slice(start, icons.indexOf(");", start));
    assert.match(body, /<svg \{\.\.\.glyph\}>/, name);
    assert.doesNotMatch(body, /fill=|Gradient|<text/, name);
    const shapes = (body.match(/<(path|circle|rect)\b/g) ?? []).length;
    assert.ok(shapes >= 2 && shapes <= 4, `${name} has ${shapes} shapes`);
  }
});

test("the owner's collection descriptions keep the brief's limits", () => {
  const byId = Object.fromEntries(STOREFRONT_CATALOG.map((entry) => [entry.id, entry]));
  for (const entry of STOREFRONT_CATALOG) {
    assert.doesNotMatch(entry.blurb, /\bevery\b/i, `${entry.id}: "every" needs a release to substantiate it`);
  }
  assert.doesNotMatch(byId.nagpra.blurb, /outstanding/i, "no outstanding-claim status Cedar cannot establish");
  assert.doesNotMatch(byId.nonprofits.blurb, /year over year|annual/i, "no annual comparison before the series ships");
  assert.match(byId.nonprofits.blurb, /Native-led and Native-serving as the same thing/);
});

// ── Rotation ──────────────────────────────────────────────────────────────

const run = (state, ...actions) => actions.reduce((s, a) => rotationReducer(s, { total: 9, ...a }), state);
const onScreen = run(INITIAL_ROTATION, { type: "visible", on: true });

test("the step is slow: inside the brief's seven to nine seconds", () => {
  assert.ok(ROTATE_MS >= 7000 && ROTATE_MS <= 9000, String(ROTATE_MS));
});

test("it advances on screen and wraps round", () => {
  assert.equal(run(onScreen, { type: "tick" }).index, 1);
  assert.equal(run({ ...onScreen, index: 8 }, { type: "tick" }).index, 0);
  assert.equal(run(INITIAL_ROTATION, { type: "tick" }).index, 0, "off screen, nothing moves");
});

test("hover and focus pause it, and releasing them resumes it", () => {
  const hovered = run(onScreen, { type: "hover", on: true });
  assert.equal(shouldRotate(hovered, { total: 9 }), false);
  assert.equal(run(hovered, { type: "tick" }).index, 0);
  const focused = run(onScreen, { type: "focus", on: true });
  assert.equal(shouldRotate(focused, { total: 9 }), false);
  assert.equal(run(focused, { type: "tick" }).index, 0);
  assert.equal(shouldRotate(run(hovered, { type: "hover", on: false }), { total: 9 }), true);
});

test("any choice stops it for good, and a late tick cannot move the chosen example", () => {
  for (const action of [{ type: "select", index: 4 }, { type: "next" }, { type: "prev" }]) {
    const chosen = run(onScreen, action);
    assert.equal(chosen.stopped, true, action.type);
    assert.equal(shouldRotate(chosen, { total: 9 }), false, action.type);
    assert.equal(run(chosen, { type: "tick" }).index, chosen.index, `${action.type} then tick`);
    // Leaving and re-entering does not restart it.
    const back = run(chosen, { type: "hover", on: true }, { type: "hover", on: false }, { type: "visible", on: true });
    assert.equal(shouldRotate(back, { total: 9 }), false, action.type);
  }
  assert.equal(run(onScreen, { type: "prev" }).index, 8, "previous from the first wraps to the last");
  assert.equal(run(onScreen, { type: "select", index: -1 }).index, 8);
});

test("committing a collection stops the rotation and keeps the example in place", () => {
  const moved = run(onScreen, { type: "tick" }, { type: "tick" });
  const committed = run(moved, { type: "stop" });
  assert.equal(committed.index, moved.index);
  assert.equal(committed.stopped, true);
  assert.equal(run(committed, { type: "tick" }).index, moved.index);
});

test("rotation state carries no collection: only a visitor's click selects one", () => {
  const after = run(onScreen, { type: "tick" }, { type: "tick" }, { type: "next" }, { type: "stop" });
  assert.deepEqual(Object.keys(after).sort(), ["focused", "hovered", "index", "stopped", "visible"]);
});

test("reduced motion never cycles, and one example has nothing to cycle", () => {
  assert.equal(shouldRotate(onScreen, { total: 9 }), true);
  assert.equal(shouldRotate(onScreen, { total: 9, reducedMotion: true }), false);
  assert.equal(shouldRotate(onScreen, { total: 1 }), false);
  assert.equal(rotationReducer(onScreen, { type: "nonsense" }), onScreen);
});

test("the counter counts what is shown", () => {
  assert.equal(counterLabel(0, visibleAudiences().length), "01 / 09");
  assert.equal(counterLabel(9, 10), "10 / 10");
});
