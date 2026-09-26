/**
 * The door's use-case band: the gate between released and announced
 * collections, the switch from interim copy to the owner's launch copy,
 * coverage, and the rotation rules.
 *
 * THE GATE IS THAT THE PAGE NEVER LOADS THE ANNOUNCED MATERIAL. Runtime code
 * (`pressAudiences.js`, `COLLECTION_ICONS`) holds released collections only;
 * the announced ones and every sentence about them live in
 * `pressAnnounced.js` and `pressAnnouncedIcons.jsx`, which only tests import.
 * So these tests prove two things: nothing the page loads reaches those
 * files, and when the material IS merged in (`withLaunchCopy`, a launched
 * catalog) the runtime gate picks the owner's copy with no other change. The
 * smoke suite's "the bundle" test proves the first against the real build.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

import { PRESS_CATALOG, STOREFRONT_CATALOG } from "./pressCatalog.js";
import {
  ANNOUNCED_AUDIENCES,
  ANNOUNCED_COLLECTIONS,
  ANNOUNCED_IDS,
  LAUNCH_COPY,
  gatedPhrases,
  isAnnounced,
  isCitable,
  launchedCatalog,
  withLaunchCopy,
} from "./pressAnnounced.js";
import {
  INITIAL_ROTATION,
  MIN_COLLECTIONS,
  PRESS_AUDIENCES,
  ROTATE_MS,
  citedIds,
  counterLabel,
  liveCollection,
  liveIdsOf,
  resolveAudience,
  rotationReducer,
  shouldRotate,
  uncoveredIds,
  visibleAudiences,
} from "./pressAudiences.js";

const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8");
const SRC = new URL("../../", import.meta.url);

/** Every audience as it will stand at launch, with the gated sentences merged in. */
const ALL = withLaunchCopy();

/** Words a sentence may not use while the giving and parcel collections are gated. */
const GATED_SUBJECT = /parcel|property|philanthrop|private giving|foundation/i;

// ── The gate: the page never loads the announced material ─────────────────

/** Every non-test source file under src/, with its path relative to src/. */
function runtimeSources() {
  const out = [];
  for (const entry of readdirSync(SRC, { recursive: true, withFileTypes: true })) {
    if (!entry.isFile() || !/\.(jsx?|mjs)$/.test(entry.name) || /\.test\./.test(entry.name)) continue;
    const dir = entry.parentPath ?? entry.path;
    const full = `${dir}/${entry.name}`;
    out.push({ rel: full.slice(SRC.pathname.length), text: readFileSync(full, "utf8") });
  }
  return out;
}

test("nothing the page loads imports the announced material", () => {
  const sources = runtimeSources();
  assert.ok(sources.length > 50, "found the source tree");
  for (const { rel, text } of sources) {
    if (rel.endsWith("features/grove/pressAnnounced.js") || rel.endsWith("pages/grove/pressAnnouncedIcons.jsx")) continue;
    assert.doesNotMatch(text, /from\s+["'][^"']*pressAnnounced(Icons)?(\.jsx?)?["']/, `${rel} imports the announced material`);
    assert.doesNotMatch(text, /import\(\s*["'][^"']*pressAnnounced/, `${rel} imports the announced material dynamically`);
  }
});

test("no runtime module states a gated name, description or sentence", () => {
  // The bundle test proves this against the build; this names the file first.
  const phrases = gatedPhrases().filter((phrase) => phrase.length > 4);
  for (const { rel, text } of runtimeSources()) {
    if (/pressAnnounced(Icons)?\.jsx?$/.test(rel)) continue;
    for (const phrase of phrases) assert.ok(!text.includes(phrase), `${rel} states "${phrase.slice(0, 40)}"`);
  }
});

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

test("launch copy whose collections are all released has been moved into the page", () => {
  const live = liveIdsOf();
  for (const [id, copy] of Object.entries(LAUNCH_COPY)) {
    assert.ok(PRESS_AUDIENCES.some((audience) => audience.id === id), `launch copy for an unknown audience: ${id}`);
    assert.ok(
      !copy.collections.every((cid) => live.has(cid)),
      `${id}'s launch copy cites only released collections: move it into pressAudiences.js as atLaunch`,
    );
  }
  for (const { after, audience } of ANNOUNCED_AUDIENCES) {
    assert.ok(PRESS_AUDIENCES.some((a) => a.id === after), `${audience.id} anchors on unknown ${after}`);
    assert.ok(!PRESS_AUDIENCES.some((a) => a.id === audience.id), `${audience.id} is both announced and on the page`);
    assert.ok(!audience.atLaunch.collections.every((cid) => live.has(cid)), `${audience.id} is fully released: move it`);
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
  for (const id of citedIds(ALL)) {
    assert.ok(isCitable(id), `${id} is neither in the catalog nor announced`);
  }
  assert.equal(isCitable("gaming"), false, "an id nobody declared is refused");
});

test("today, no shown audience cites a gated collection or talks about one", () => {
  for (const audiences of [PRESS_AUDIENCES, ALL]) {
    const shown = visibleAudiences(STOREFRONT_CATALOG, audiences);
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
  const ids = visibleAudiences(STOREFRONT_CATALOG, ALL).map((audience) => audience.id);
  assert.ok(!ids.includes("foundations-philanthropy"));
  assert.equal(ids.length, ALL.length - 1);
  assert.equal(resolveAudience(ALL.find((a) => a.id === "foundations-philanthropy")), null);
  assert.deepEqual(visibleAudiences().map((a) => a.id), ids, "the page shows exactly what the merged set shows today");
});

test("an audience with fewer than three live collections is hidden rather than shown thin", () => {
  const thin = { id: "thin", label: "Thin", atLaunch: { use: "x", collections: ["funding", "deals"] }, now: null };
  assert.equal(resolveAudience(thin), null);
});

// ── Flipping the gate ─────────────────────────────────────────────────────

test("launching both collections switches every audience to the owner's copy", () => {
  const shown = visibleAudiences(launchedCatalog(), ALL);
  assert.equal(shown.length, 10, "all ten, Foundations included");
  assert.equal(shown[5].id, "foundations-philanthropy", "back in its place, after Native nonprofits");
  for (const audience of shown) {
    const declared = ALL.find((a) => a.id === audience.id);
    assert.equal(audience.version, "atLaunch", audience.id);
    assert.equal(audience.use, declared.atLaunch.use, audience.id);
    assert.deepEqual(audience.collections.map((entry) => entry.id), [...declared.atLaunch.collections]);
  }
  assert.equal(counterLabel(0, shown.length), "01 / 10");
});

test("launching one collection switches only the audiences that cite nothing else gated", () => {
  const byId = Object.fromEntries(visibleAudiences(launchedCatalog(["plot"]), ALL).map((a) => [a.id, a]));
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
  const catalog = launchedCatalog();
  assert.equal(catalog.length, 14);
  assert.deepEqual(uncoveredIds(catalog, ALL), []);
  for (const id of ANNOUNCED_IDS) {
    assert.ok(
      visibleAudiences(catalog, ALL).some((audience) => audience.collections.some((entry) => entry.id === id)),
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
  for (const audience of ALL) {
    assert.doesNotMatch(audience.label, /&/, `${audience.id}: "and", never an ampersand`);
    for (const version of [audience.atLaunch, audience.now]) {
      if (!version) continue;
      assert.doesNotMatch(version.use, /[\u2014&]/, `${audience.id}: no em dash, no ampersand`);
      assert.doesNotMatch(version.use, /\bimpact\b/i, `${audience.id}: "contribution", not "impact"`);
      assert.match(version.use, /^[A-Z].*\.$/, `${audience.id}: a complete sentence`);
      assert.ok(version.collections.length >= MIN_COLLECTIONS && version.collections.length <= 5, audience.id);
    }
  }
});

test("the band names collections by id only: no second catalog", () => {
  const catalogIds = new Set(PRESS_CATALOG.map((entry) => entry.id));
  for (const id of citedIds(ALL)) assert.ok(catalogIds.has(id) || isAnnounced(id), id);
  // Neither module restates a released collection's display name.
  for (const file of ["./pressAudiences.js", "./pressAnnounced.js"]) {
    const src = read(file);
    for (const entry of PRESS_CATALOG) {
      assert.ok(!src.includes(`name: "${entry.name}"`), `${file} restates ${entry.id}`);
    }
  }
  assert.doesNotMatch(read("./pressAudiences.js"), /\bshort:/, "the runtime module defines no collection");
});

test("every live collection has a mark, and both announced marks are drawn with the family", () => {
  const family = read("../../pages/grove/pressCollectionIcons.jsx");
  const announced = read("../../pages/grove/pressAnnouncedIcons.jsx");
  const keyedIn = (src, id) =>
    new RegExp(`(^|\\s)(${id}|"${id}"):\\s*\\w+Icon,`, "m").test(src.slice(src.search(/export const \w+_ICONS/)));
  for (const entry of STOREFRONT_CATALOG) assert.ok(keyedIn(family, entry.id), `no mark for ${entry.id}`);
  for (const entry of ANNOUNCED_COLLECTIONS) {
    assert.ok(keyedIn(announced, entry.icon), `no announced mark for ${entry.id}`);
    assert.ok(!keyedIn(family, entry.icon), `${entry.id}'s mark is in the runtime family before launch`);
  }
  // Same family: identical glyph props, no fills, no gradients, two to four shapes.
  const glyph = (src) => src.slice(src.indexOf("const glyph = {"), src.indexOf("};", src.indexOf("const glyph = {")));
  assert.equal(glyph(announced), glyph(family), "the announced marks use the family's exact glyph props");
  for (const name of ["GivingIcon", "PlotIcon"]) {
    const start = announced.indexOf(`const ${name} = (`);
    assert.ok(start >= 0, name);
    const body = announced.slice(start, announced.indexOf(");", start));
    assert.match(body, /<svg \{\.\.\.glyph\}>/, name);
    assert.doesNotMatch(body, /fill=|Gradient|<text/, name);
    const shapes = (body.match(/<(path|circle|rect)\b/g) ?? []).length;
    assert.ok(shapes >= 2 && shapes <= 4, `${name} has ${shapes} shapes`);
  }
});

test("the gated phrase list covers every name, description and gated sentence", () => {
  const phrases = gatedPhrases();
  for (const entry of ANNOUNCED_COLLECTIONS) {
    for (const value of [entry.name, entry.blurb, entry.id]) assert.ok(phrases.includes(value), value);
  }
  assert.ok(phrases.includes("Foundations and philanthropy"));
  assert.ok(phrases.some((p) => p.includes("parcel activity")), "the owner's banks sentence");
  // The advisors sentence is the owner's and already ships as interim copy.
  assert.ok(!phrases.includes(LAUNCH_COPY.advisors.use));
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
