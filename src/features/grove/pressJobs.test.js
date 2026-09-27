/**
 * The shared jobs layer (`pressJobs.js`) and the gate around what it may say.
 *
 *   single source   no page types a question, outcome, example or line the
 *                   layer owns; every surface reads it
 *   answerable      every collection question names codebook fields that
 *                   exist; Cedar's suggestions are held to the profile router
 *                   by the Python suite (server/tests/test_cedar_questions.py)
 *   the gate        runtime code holds released collections only; the
 *                   announced ones and every sentence about them live in
 *                   `pressAnnounced.js` and `pressAnnouncedIcons.jsx`, which
 *                   only tests import, and when they ARE merged in the
 *                   runtime gate picks the owner's copy with no other change
 *   coverage        a REPORT, not a rule (owner, 2026-09-26)
 *   imagery         every photograph a use case can show is copied in, at
 *                   the sizes declared, and has a license record
 *
 * The smoke suite's "the bundle" test proves the gate against the real build.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

import codebookJson from "../../../data/cedar/codebook.json" with { type: "json" };
import { PRESS_CATALOG, STOREFRONT_CATALOG } from "./pressCatalog.js";
import {
  ANNOUNCED_AUDIENCES,
  ANNOUNCED_COLLECTIONS,
  ANNOUNCED_COLLECTION_JOBS,
  ANNOUNCED_ECOSYSTEM_EXAMPLES,
  ANNOUNCED_IDS,
  LAUNCH_COPY,
  gatedPhrases,
  isAnnounced,
  isCitable,
  launchedCatalog,
  withLaunchCopy,
} from "./pressAnnounced.js";
import { SECTOR_IMAGES, imageFile, imageSources } from "./pressImagery.js";
import { BUILD_NEXT_QUESTION, BUILD_NEXT_STEPS, ECOSYSTEM_EXAMPLES } from "./pressMethod.js";
import { PRIORITY_EXAMPLES } from "./pressPriorities.js";
import { catalogDescription } from "../../../scripts/seo-head.mjs";
import {
  AUDIENCE_JOBS,
  BAND_NOTE,
  CEDAR_CHANGES_QUESTION,
  COLLECTION_JOBS,
  ENTITY_JOBS,
  JOBS,
  MIN_COLLECTIONS,
  QUESTION_KINDS,
  cedarQuestions,
  citedIds,
  collectionQuestions,
  entityActions,
  liveCollection,
  liveIdsOf,
  openCedarQuestions,
  researchExamples,
  resolveAudience,
  uncoveredIds,
  visibleAudiences,
} from "./pressJobs.js";

const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8");
const SRC = new URL("../../", import.meta.url);
const ROOT = new URL("../../../", import.meta.url);

/** Every audience as it will stand at launch, with the gated sentences merged in. */
const ALL = withLaunchCopy();

/** Words an interim sentence may not use while the giving and parcel collections are gated. */
const GATED_SUBJECT = /parcel|property|\bland\b|permit|philanthrop|private giving|private support|foundation|funders\b/i;

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

// ── Single source: no page hard-codes what the layer owns ─────────────────

/** Every string the jobs layer owns, which no other runtime file may state. */
function ownedStrings() {
  const out = new Set([BAND_NOTE, ENTITY_JOBS.line, CEDAR_CHANGES_QUESTION.q]);
  for (const jobs of Object.values(COLLECTION_JOBS)) {
    for (const item of [...jobs.questions, ...jobs.cedar]) out.add(item.q);
  }
  for (const audience of AUDIENCE_JOBS) {
    out.add(audience.outcome);
    for (const version of [audience.atLaunch, audience.now]) if (version) out.add(version.explanation);
    if (audience.researchExample) out.add(audience.researchExample.text);
  }
  for (const action of ENTITY_JOBS.actions) out.add(action.label);
  return [...out];
}

/** Source text with every run of whitespace, JSX line breaks included, as one space. */
const flat = (text) => text.replace(/\s+/g, " ");

test("no page hard-codes a question, outcome, example or line the jobs layer owns", () => {
  const owned = ownedStrings();
  assert.ok(owned.length > 60, `the layer owns ${owned.length} strings: the check would pass vacuously`);
  for (const { rel, text } of runtimeSources()) {
    if (rel.endsWith("features/grove/pressJobs.js")) continue;
    const body = flat(text);
    for (const phrase of owned) {
      assert.ok(!body.includes(flat(phrase)), `${rel} types "${phrase.slice(0, 50)}": read it from pressJobs.js`);
    }
  }
});

test("every surface the brief names reads the layer", () => {
  const readers = {
    "pages/grove/PressAudienceExample.jsx": /visibleAudiences|BAND_NOTE/,
    "pages/grove/PressCollectionAbout.jsx": /collectionQuestions/,
    "features/grove/readerCedar.js": /cedarQuestions|openCedarQuestions/,
    "pages/grove/CedarPress.jsx": /openCedarQuestions/,
    "pages/grove/CedarPressEntity.jsx": /ENTITY_JOBS|entityActions/,
    "pages/grove/CedarPressResearchAccess.jsx": /researchExamples/,
  };
  for (const [rel, uses] of Object.entries(readers)) {
    const src = read(`../../${rel}`);
    assert.match(src, /from\s+["'][^"']*pressJobs(\.js)?["']/, `${rel} does not import the jobs layer`);
    assert.match(src, uses, `${rel} does not read what it shows from the layer`);
  }
});

// ── Answerable: every collection question names fields that exist ─────────

/** The codebook table a collection's questions are checked against. */
function codebookTable(id) {
  const keys = Object.keys(codebookJson.tables).filter((key) => key.split("/")[0] === id);
  return keys.length === 1 ? codebookJson.tables[keys[0]] : null;
}

test("every live collection has two or three questions, and nothing else does", () => {
  const live = liveIdsOf();
  for (const entry of STOREFRONT_CATALOG) {
    const questions = collectionQuestions(entry.id);
    assert.ok(questions.length >= 2 && questions.length <= 3, `${entry.id} has ${questions.length} questions`);
    assert.ok(cedarQuestions(entry.id).length >= 2, `${entry.id} offers Cedar nothing to answer`);
  }
  for (const id of Object.keys(COLLECTION_JOBS)) assert.ok(live.has(id), `questions for ${id}, which is not live`);
  assert.deepEqual(collectionQuestions("not-a-collection"), []);
  assert.deepEqual(cedarQuestions("not-a-collection"), []);
});

test("every collection question rests on fields its codebook table holds", () => {
  let checked = 0;
  for (const [id, jobs] of Object.entries(COLLECTION_JOBS)) {
    const table = codebookTable(id);
    assert.ok(table, `${id} has no single codebook table to check its questions against`);
    const columns = new Set(table.fields.map((field) => field.column));
    for (const item of jobs.questions) {
      assert.ok(item.fields.length, `"${item.q}" names no field`);
      for (const column of item.fields) {
        assert.ok(columns.has(column), `"${item.q}" rests on ${column}, which ${id}'s codebook does not hold`);
        checked += 1;
      }
    }
  }
  assert.ok(checked > 60, `only ${checked} fields checked`);
});

test("every question carries a kind, and each collection mixes them", () => {
  const kinds = new Set(Object.values(QUESTION_KINDS));
  assert.deepEqual([...kinds].sort(), ["Compare", "Describe", "Trace"]);
  for (const [id, jobs] of Object.entries(COLLECTION_JOBS)) {
    for (const item of [...jobs.questions, ...jobs.cedar]) assert.ok(kinds.has(item.kind), `${id}: "${item.q}" has kind ${item.kind}`);
    const mix = new Set(jobs.questions.map((item) => item.kind));
    assert.ok(mix.size >= 2, `${id}'s questions are all ${[...mix][0]}`);
  }
  assert.ok(kinds.has(CEDAR_CHANGES_QUESTION.kind));
});

test("every Cedar suggestion names the profile branch that answers it", () => {
  // The Python suite runs each through `answer_from_profile` and holds it to
  // this branch; here, only that the branch is one the profile has.
  for (const id of Object.keys(COLLECTION_JOBS)) {
    const asked = cedarQuestions(id);
    assert.equal(asked.at(-1), CEDAR_CHANGES_QUESTION, `${id}: the release question comes last`);
    for (const item of asked) assert.ok(["content", "construct", "changes"].includes(item.route), `${id}: "${item.q}"`);
    assert.equal(new Set(asked.map((item) => item.q)).size, asked.length, `${id} repeats a question`);
  }
});

test("an unscoped Cedar panel offers one question per collection, varied by position", () => {
  const entries = STOREFRONT_CATALOG.slice(0, 3);
  const open = openCedarQuestions(entries);
  assert.equal(open.length, 3);
  open.forEach((item, i) => {
    assert.equal(item.scope.id, entries[i].id);
    assert.equal(item.q, cedarQuestions(entries[i].id)[i % cedarQuestions(entries[i].id).length].q);
  });
  assert.deepEqual(openCedarQuestions([{ id: "nope", name: "Nope" }]), []);
});

test("questions keep the house style", () => {
  for (const [id, jobs] of Object.entries(COLLECTION_JOBS)) {
    for (const item of [...jobs.questions, ...jobs.cedar]) {
      assert.match(item.q, /^[A-Z][^&—]*\?$/, `${id}: "${item.q}" is not one plain question`);
    }
  }
  for (const jobs of Object.values(ANNOUNCED_COLLECTION_JOBS)) {
    for (const question of jobs.questions) assert.match(question, /^[A-Z][^&—]*\?$/, question);
  }
});

// ── The gate: the page never loads the announced material ─────────────────

test("nothing the page loads imports the announced material", () => {
  const sources = runtimeSources();
  assert.ok(sources.length > 50, "found the source tree");
  for (const { rel, text } of sources) {
    if (rel.endsWith("features/grove/pressAnnounced.js") || rel.endsWith("pages/grove/pressAnnouncedIcons.jsx")) continue;
    assert.doesNotMatch(text, /from\s+["'][^"']*pressAnnounced(Icons)?(\.jsx?)?["']/, `${rel} imports the announced material`);
    assert.doesNotMatch(text, /import\(\s*["'][^"']*pressAnnounced/, `${rel} imports the announced material dynamically`);
  }
});

test("no runtime module states a gated name, description, question or sentence", () => {
  // The bundle test proves this against the build; this names the file first.
  const phrases = gatedPhrases().filter((phrase) => phrase.length > 4);
  for (const { rel, text } of runtimeSources()) {
    if (/pressAnnounced(Icons)?\.jsx?$/.test(rel)) continue;
    const body = flat(text);
    for (const phrase of phrases) assert.ok(!body.includes(flat(phrase)), `${rel} states "${phrase.slice(0, 40)}"`);
  }
});

test("the announced collections are declared once, and are not in the catalog or the jobs layer", () => {
  assert.deepEqual([...ANNOUNCED_IDS].sort(), ["foundation-corporate-giving", "plot"]);
  const catalogIds = new Set(PRESS_CATALOG.map((entry) => entry.id));
  for (const id of ANNOUNCED_IDS) {
    assert.ok(!catalogIds.has(id), `${id} is both announced and in the catalog: move it, do not copy it`);
    assert.ok(!COLLECTION_JOBS[id], `${id}'s questions are in the runtime layer before launch`);
    assert.ok(ANNOUNCED_COLLECTION_JOBS[id]?.questions.length >= 2, `${id} has no questions waiting for launch`);
  }
  for (const entry of ANNOUNCED_COLLECTIONS) {
    assert.ok(entry.name && entry.short && entry.blurb && entry.icon, entry.id);
  }
});

test("launch copy whose collections are all released has been moved into the page", () => {
  const live = liveIdsOf();
  for (const [id, copy] of Object.entries(LAUNCH_COPY)) {
    assert.ok(AUDIENCE_JOBS.some((audience) => audience.id === id), `launch copy for an unknown audience: ${id}`);
    assert.ok(
      !copy.collections.every((cid) => live.has(cid)),
      `${id}'s launch copy cites only released collections: move it into pressJobs.js as atLaunch`,
    );
  }
  for (const { after, audience } of ANNOUNCED_AUDIENCES) {
    assert.ok(AUDIENCE_JOBS.some((a) => a.id === after), `${audience.id} anchors on unknown ${after}`);
    assert.ok(!AUDIENCE_JOBS.some((a) => a.id === audience.id), `${audience.id} is both announced and on the page`);
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

test("today, no shown audience cites a gated collection, and no interim sentence talks about one", () => {
  for (const audiences of [AUDIENCE_JOBS, ALL]) {
    const shown = visibleAudiences(STOREFRONT_CATALOG, audiences);
    assert.ok(shown.length);
    for (const audience of shown) {
      for (const entry of audience.collections) {
        assert.ok(entry, `${audience.id} resolved a missing collection`);
        assert.ok(!isAnnounced(entry.id), `${audience.id} shows ${entry.id}`);
      }
      if (audience.version === "now") {
        assert.doesNotMatch(audience.explanation, GATED_SUBJECT, `${audience.id}'s interim copy names a gated subject`);
      }
      assert.ok(audience.collections.length >= MIN_COLLECTIONS, `${audience.id} is too thin to show`);
    }
  }
});

test("every interim sentence cites live collections only and names no gated subject", () => {
  // The bundle proof cannot see this case: a gated sentence moved into
  // AUDIENCE_JOBS is, by that move, declared released. So the interim copy
  // itself is held to naming nothing only a gated collection covers.
  const gated = new Set(ANNOUNCED_IDS);
  for (const audience of AUDIENCE_JOBS) {
    if (!audience.now) continue;
    for (const id of audience.now.collections) assert.ok(!gated.has(id), `${audience.id} now cites ${id}`);
    assert.doesNotMatch(audience.now.explanation, GATED_SUBJECT, audience.id);
  }
});

test("an audience that exists only for a gated collection is hidden until launch", () => {
  const ids = visibleAudiences(STOREFRONT_CATALOG, ALL).map((audience) => audience.id);
  assert.ok(!ids.includes("foundations-philanthropy"));
  assert.equal(ids.length, ALL.length - 1);
  assert.equal(resolveAudience(ALL.find((a) => a.id === "foundations-philanthropy")), null);
  assert.deepEqual(visibleAudiences().map((a) => a.id), ids, "the page shows exactly what the merged set shows today");
});

test("Foundations and philanthropy says, at launch, that it is not a need score", () => {
  // The owner's caution: observable indicators of funding and activity, never
  // a definitive need score. Held here so the launch cannot drop it.
  const foundations = ANNOUNCED_AUDIENCES.find(({ audience }) => audience.id === "foundations-philanthropy").audience;
  assert.match(foundations.atLaunch.explanation, /not a need score/);
  // And nowhere else does it claim to measure need.
  const rest = `${foundations.outcome} ${foundations.atLaunch.explanation}`.replace(/not a need score/g, "");
  assert.doesNotMatch(rest, /need score|scores? (of|for) need|need index|rank\w* need|most in need/i);
});

test("an audience with fewer than three live collections is hidden rather than shown thin", () => {
  const thin = { id: "thin", audience: "Thin", job: "Research", outcome: "x", atLaunch: { explanation: "x", collections: ["funding", "deals"] }, now: null };
  assert.equal(resolveAudience(thin), null);
});

// ── Flipping the gate ─────────────────────────────────────────────────────

test("launching both collections switches every audience to the owner's copy", () => {
  const shown = visibleAudiences(launchedCatalog(), ALL);
  assert.equal(shown.length, 11, "all eleven, Foundations included");
  assert.equal(shown[5].id, "foundations-philanthropy", "back in its place, after Native nonprofits");
  for (const audience of shown) {
    const declared = ALL.find((a) => a.id === audience.id);
    assert.equal(audience.version, "atLaunch", audience.id);
    assert.equal(audience.explanation, declared.atLaunch.explanation, audience.id);
    assert.equal(audience.outcome, declared.outcome, audience.id);
    assert.deepEqual(audience.collections.map((entry) => entry.id), [...declared.atLaunch.collections]);
  }
});

test("launching one collection switches only the audiences that cite nothing else gated", () => {
  const byId = Object.fromEntries(visibleAudiences(launchedCatalog(["plot"]), ALL).map((a) => [a.id, a]));
  // Cites PLOT and nothing else gated: the owner's copy.
  assert.equal(byId["ancs-nhos"].version, "atLaunch");
  assert.equal(byId["banks-lenders"].version, "atLaunch");
  // Cites the giving collection: still interim, or still hidden.
  assert.equal(byId["native-nonprofits"].version, "now");
  assert.equal(byId["foundations-philanthropy"], undefined);
});

test("where the owner's sentence cites only live collections, it is the copy today", () => {
  const byId = Object.fromEntries(visibleAudiences().map((a) => [a.id, a]));
  for (const id of ["tribal-nations", "native-enterprises", "businesses", "universities-researchers", "advisors", "economic-development"]) {
    assert.equal(byId[id].version, "atLaunch", id);
  }
  assert.equal(byId["economic-development"].audience, "Economic development, investors and outside partners");
});

// ── Coverage: a report for review, not a rule ─────────────────────────────

test("coverage report: live collections no shown use case names", (t) => {
  // Owner, 2026-09-26: "The landing page should show the best reasons to use
  // Cedar Press, not prove that each dataset got a turn." So this reports and
  // never fails; docs/DESIGN_SYSTEM.md carries the same list for review.
  const today = uncoveredIds();
  const atLaunch = uncoveredIds(launchedCatalog(), ALL);
  t.diagnostic(`uncovered today: ${today.length ? today.join(", ") : "none"}`);
  t.diagnostic(`uncovered with the gate open: ${atLaunch.length ? atLaunch.join(", ") : "none"}`);
});

test("the coverage report names a collection that loses its last use case", () => {
  // The report's mechanism, not a coverage rule: it has to be able to see a gap.
  const withoutNagpra = AUDIENCE_JOBS.map((audience) => ({
    ...audience,
    atLaunch: audience.atLaunch && {
      ...audience.atLaunch,
      collections: audience.atLaunch.collections.map((id) => (id === "nagpra" ? "funding" : id)),
    },
  }));
  assert.deepEqual(uncoveredIds(STOREFRONT_CATALOG, withoutNagpra), ["nagpra"]);
});

// ── Copy and data rules ───────────────────────────────────────────────────

test("every use case has a job from the shared vocabulary", () => {
  assert.equal(JOBS.length, 11);
  assert.ok(JOBS.includes("Competitive intelligence"), "the owner's job for ANCs and NHOs");
  for (const audience of ALL) assert.ok(JOBS.includes(audience.job), `${audience.id}: "${audience.job}" is not a job`);
});

test("labels, outcomes and sentences keep the house style", () => {
  for (const audience of ALL) {
    assert.doesNotMatch(audience.audience, /&/, `${audience.id}: "and", never an ampersand`);
    assert.match(audience.outcome, /^[A-Z][^&—]*\.$/, `${audience.id}: the outcome is one plain sentence`);
    for (const version of [audience.atLaunch, audience.now]) {
      if (!version) continue;
      assert.doesNotMatch(version.explanation, /[—&]/, `${audience.id}: no em dash, no ampersand`);
      assert.doesNotMatch(version.explanation, /\bimpact\b/i, `${audience.id}: "contribution", not "impact"`);
      assert.match(version.explanation, /^[A-Z].*\.$/, `${audience.id}: complete sentences`);
      assert.ok(version.collections.length >= MIN_COLLECTIONS && version.collections.length <= 6, audience.id);
    }
  }
  for (const line of [BAND_NOTE, ENTITY_JOBS.line]) assert.match(line, /^[A-Z][^&—]*\.$/, line);
});

test("the layer names collections by id only: no second catalog", () => {
  const catalogIds = new Set(PRESS_CATALOG.map((entry) => entry.id));
  for (const id of citedIds(ALL)) assert.ok(catalogIds.has(id) || isAnnounced(id), id);
  for (const file of ["./pressJobs.js", "./pressAnnounced.js"]) {
    const src = read(file);
    for (const entry of PRESS_CATALOG) {
      assert.ok(!src.includes(`name: "${entry.name}"`), `${file} restates ${entry.id}`);
    }
  }
  assert.doesNotMatch(read("./pressJobs.js"), /\bshort:/, "the runtime module defines no collection");
});

test("research access examples cite live collections, and name each one they cite", () => {
  const examples = researchExamples();
  assert.equal(examples.length, 2);
  for (const example of examples) {
    for (const entry of example.collections) {
      assert.ok(entry, `${example.id} cites a collection that is not live`);
      assert.ok(example.text.includes(entry.short), `${example.id} cites ${entry.id} without naming it`);
    }
  }
  const gated = [{ id: "x", researchExample: { text: "PLOT only.", collections: ["plot"] } }];
  assert.deepEqual(researchExamples(STOREFRONT_CATALOG, gated), [], "an example citing a gated collection is not offered");
});

test("the entity page offers only the actions that work today", () => {
  const shown = entityActions().map((action) => action.id);
  assert.deepEqual(shown, ["related", "over-time"]);
  for (const action of ENTITY_JOBS.actions.filter((a) => !a.available)) {
    assert.ok(!shown.includes(action.id), `${action.label} is not built and must not be shown`);
  }
  const related = ENTITY_JOBS.actions.find((a) => a.id === "related");
  assert.ok(liveIdsOf().has(related.collection), "related enterprises needs a live collection");
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

test("the gated phrase list covers every name, description, question and gated sentence", () => {
  const phrases = gatedPhrases();
  for (const entry of ANNOUNCED_COLLECTIONS) {
    for (const value of [entry.name, entry.blurb, entry.id]) assert.ok(phrases.includes(value), value);
  }
  for (const jobs of Object.values(ANNOUNCED_COLLECTION_JOBS)) {
    for (const question of jobs.questions) assert.ok(phrases.includes(question), question);
  }
  for (const copy of Object.values(LAUNCH_COPY)) assert.ok(phrases.includes(copy.explanation), copy.explanation);
  assert.ok(phrases.includes("Foundations and philanthropy"));
  const foundations = ANNOUNCED_AUDIENCES[0].audience;
  assert.ok(phrases.includes(foundations.outcome) && phrases.includes(foundations.atLaunch.explanation));
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

// ── Imagery ───────────────────────────────────────────────────────────────

/** A WebP's pixel size, read from its header (VP8, VP8L or VP8X). */
function webpSize(buffer) {
  const kind = buffer.toString("ascii", 12, 16);
  if (kind === "VP8X") return [1 + buffer.readUIntLE(24, 3), 1 + buffer.readUIntLE(27, 3)];
  if (kind === "VP8L") {
    const bits = buffer.readUInt32LE(21);
    return [(bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1];
  }
  if (kind === "VP8 ") return [buffer.readUInt16LE(26) & 0x3fff, buffer.readUInt16LE(28) & 0x3fff];
  throw new Error(`not a WebP: ${kind}`);
}

test("every photograph a use case can show is declared, today and at launch", () => {
  for (const audience of ALL) {
    assert.ok(audience.imagePool?.length, `${audience.id} has no image pool`);
    for (const slug of audience.imagePool) assert.ok(SECTOR_IMAGES[slug], `${audience.id} shows ${slug}, which is not declared`);
    assert.equal(new Set(audience.imagePool).size, audience.imagePool.length, `${audience.id} repeats a photograph`);
  }
  assert.equal(imageSources("nope"), null);
  const pooled = new Set(ALL.flatMap((audience) => audience.imagePool));
  for (const slug of Object.keys(SECTOR_IMAGES)) assert.ok(pooled.has(slug), `${slug} is copied in and in no pool`);
});

test("every declared photograph is copied in, at the sizes it declares, and nothing else is", () => {
  const dir = new URL("public/press/sectors/", ROOT);
  const files = new Set(readdirSync(dir));
  const expected = new Set();
  for (const [slug, entry] of Object.entries(SECTOR_IMAGES)) {
    for (const cut of ["main", "sm", "wide"]) {
      const name = imageFile(slug, cut).split("/").pop();
      expected.add(name);
      assert.ok(files.has(name), `${name} is declared and not copied in`);
      assert.deepEqual(webpSize(readFileSync(new URL(name, dir))), entry.sizes[cut], `${name} is not ${entry.sizes[cut].join("x")}`);
    }
  }
  for (const name of files) assert.ok(expected.has(name), `${name} is copied in and declared nowhere`);
});

test("every copied photograph and every use case's pool is on the license record", () => {
  const record = readFileSync(new URL("docs/IMAGE_LICENSES.md", ROOT), "utf8");
  for (const slug of Object.keys(SECTOR_IMAGES)) {
    for (const cut of ["main", "sm", "wide"]) {
      const name = imageFile(slug, cut).split("/").pop();
      assert.ok(record.includes(name), `${name} is not in docs/IMAGE_LICENSES.md`);
    }
  }
  for (const audience of ALL) {
    assert.ok(record.includes(`| ${audience.audience} |`), `${audience.audience}'s pool is not recorded`);
  }
});

test("a context texture is washed in slate, and no sector photograph is", () => {
  for (const [slug, entry] of Object.entries(SECTOR_IMAGES)) {
    assert.equal(entry.wash === "slate", slug.startsWith("context-"), slug);
    assert.equal(entry.sector === null, slug.startsWith("context-"), slug);
  }
});

// ── Counts, promotion and the owner's frame ───────────────────────────────

/** Runtime source with comments removed: what can reach a reader. */
const code = (text) => text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:\\])\/\/.*$/gm, "$1");

test("no runtime string states a collection count: every count is derived from the catalog", () => {
  for (const { rel, text } of runtimeSources()) {
    const found = code(text).match(/\b(six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|[6-9]|1\d)\s+(collections|datasets)\b/gi);
    assert.equal(found, null, `${rel} types a count: ${found}`);
  }
  // The crawler's description is generated, and counts the storefront.
  assert.match(catalogDescription(), /^Twelve collections on Indian Country's economy: federal funding, /);
  assert.match(catalogDescription(STOREFRONT_CATALOG.slice(0, 3)), /^Three collections on /);
  assert.throws(() => catalogDescription(launchedCatalog()), /no catalog phrase for (plot|foundation-corporate-giving)/, "launching one names the phrase the generator needs");
});

test("at promotion the fourteen split seven and seven: giving in Cedar Press, PLOT in Cedar Press+", () => {
  const shelves = (catalog) => ({
    standard: catalog.filter((entry) => entry.shelf === "standard").length,
    pro: catalog.filter((entry) => entry.shelf === "pro").length,
  });
  assert.deepEqual(shelves(STOREFRONT_CATALOG), { standard: 6, pro: 6 });
  assert.deepEqual(shelves(launchedCatalog()), { standard: 7, pro: 7 });
  const byId = Object.fromEntries(ANNOUNCED_COLLECTIONS.map((entry) => [entry.id, entry]));
  assert.equal(byId["foundation-corporate-giving"].shelf, "standard");
  assert.equal(byId.plot.shelf, "pro");
  for (const entry of ANNOUNCED_COLLECTIONS) assert.ok(entry.methods, `${entry.id} has no Methods concepts waiting for launch`);
});

test("cross-collection examples that need a gated collection wait in the gated layer", () => {
  assert.equal(ANNOUNCED_ECOSYSTEM_EXAMPLES.length, 2);
  for (const example of ANNOUNCED_ECOSYSTEM_EXAMPLES) {
    assert.ok(example.collections.some(isAnnounced), `${example.text.slice(0, 40)} needs nothing gated: move it into ECOSYSTEM_EXAMPLES`);
    for (const id of example.collections) assert.ok(isCitable(id), id);
    assert.ok(!ECOSYSTEM_EXAMPLES.includes(example.text));
    assert.ok(gatedPhrases().includes(example.text));
  }
  assert.deepEqual(ANNOUNCED_ECOSYSTEM_EXAMPLES.map((e) => [...e.collections].sort()), [["deals", "plot"], ["foundation-corporate-giving", "funding", "nonprofits"]]);
});

test("the time-savings sentence appears exactly once, on Research access", () => {
  const sentence = "Lumecon maintains the source trail, entity relationships and releases behind these records";
  const where = runtimeSources().filter(({ text }) => flat(text).includes(sentence)).map(({ rel }) => rel);
  assert.deepEqual(where, ["pages/grove/CedarPressResearchAccess.jsx"]);
});

test("Priorities asks what should exist next: examples, ambitious, and nothing gated", () => {
  const { datasets, research, expansions } = PRIORITY_EXAMPLES;
  assert.deepEqual(datasets.map((d) => d.theme), ["Infrastructure", "Capital access", "Housing", "Healthcare", "Energy", "Workforce"]);
  assert.ok(research.descriptive.length >= 2 && research.causal.length >= 2);
  assert.ok(expansions.length >= 2 && expansions.length < datasets.length, "the narrower asks stay the smaller set");
  const all = [...datasets.map((d) => d.text), ...research.descriptive, ...research.causal, ...expansions];
  for (const text of all) {
    assert.doesNotMatch(text, /[&\u2014]/, text);
    assert.doesNotMatch(text, /\bimpact\b/i, text);
    assert.doesNotMatch(text, /parcel|permit|land ownership|philanthrop|foundation|corporate giving|PLOT/i, `${text}: names a gated subject before launch`);
  }
  for (const text of research.causal) assert.match(text, /^(Did|Does|How much|Why|What caused)/, `${text} does not read as causal`);
});

test("Methods says how Cedar decides what to build next, from the owner's question", () => {
  assert.equal(BUILD_NEXT_QUESTION, "What important question can I not answer today?");
  assert.deepEqual(BUILD_NEXT_STEPS.map((step) => step.label), [
    "Question",
    "Source investigation",
    "Research and collection design",
    "Validation",
    "Release",
    "Maintenance",
  ]);
  const src = code(read("../../pages/grove/CedarPressMethods.jsx"));
  assert.match(src, /BUILD_NEXT_QUESTION/);
  assert.match(src, /Unjoined files can be searched\. Identified records can be counted, compared and\s+traced across sources\./);
  assert.doesNotMatch(src, /A model reading/);
});
