/**
 * The shared jobs layer (`pressJobs.js`) and the gate around what it may say.
 *
 *   single source   no page types a question, outcome, example or line the
 *                   layer owns; every surface reads it
 *   answerable      every collection question names codebook fields that
 *                   exist; Cedar's suggestions are held to the profile router
 *                   by the Python suite (server/tests/test_cedar_questions.py)
 *   the owner's copy every audience shows the owner's sentence, and all
 *                   eleven show against the fourteen-collection catalog
 *   coverage        a REPORT, not a rule (owner, 2026-09-26)
 *   imagery         every photograph a use case can show is copied in, at
 *                   the sizes declared, and has a license record
 *
 * The smoke suite's "the bundle" test proves both new collections, their
 * questions and the owner's sentences are in the real build.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

import codebookJson from "../../../data/cedar/codebook.json" with { type: "json" };
import { PRESS_CATALOG, STOREFRONT_CATALOG } from "./pressCatalog.js";
import { PENDING_RELEASE, isReleased } from "./collection.js";
import { SECTOR_IMAGES, imageFile, imageSources } from "./pressImagery.js";
import { BUILD_NEXT_QUESTION, BUILD_NEXT_STEPS, ECOSYSTEM_EXAMPLES } from "./pressMethod.js";
import { PRIORITY_EXAMPLES } from "./pressPriorities.js";
import { catalogDescription } from "../../../scripts/seo-head.mjs";
import {
  ALL_COLLECTION_JOBS,
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

/** Every audience. */
const ALL = AUDIENCE_JOBS;

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
  for (const jobs of Object.values(ALL_COLLECTION_JOBS)) {
    for (const item of [...jobs.questions, ...(jobs.cedar ?? [])]) out.add(item.q);
  }
  for (const audience of AUDIENCE_JOBS) {
    out.add(audience.outcome);
    out.add(audience.explanation);
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

test("every collection has two or three questions, and nothing else does", () => {
  const live = liveIdsOf();
  assert.equal(STOREFRONT_CATALOG.length, 14);
  for (const entry of STOREFRONT_CATALOG) {
    const questions = collectionQuestions(entry.id);
    assert.ok(questions.length >= 2 && questions.length <= 3, `${entry.id} has ${questions.length} questions`);
    // Cedar answers from a release profile, so only a released collection
    // offers it anything; a pending one offers nothing rather than a
    // question the router would refuse.
    if (isReleased(entry.id)) {
      assert.ok(cedarQuestions(entry.id).length >= 2, `${entry.id} offers Cedar nothing to answer`);
    } else {
      assert.deepEqual(cedarQuestions(entry.id), [], `${entry.id} has no release for Cedar to answer from`);
    }
  }
  for (const id of Object.keys(ALL_COLLECTION_JOBS)) assert.ok(live.has(id), `questions for ${id}, which is not in the catalog`);
  for (const id of Object.keys(COLLECTION_JOBS)) assert.ok(isReleased(id), `${id} carries Cedar questions with no release`);
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

/**
 * The columns the producer declares for Foundation & Corporate Giving's
 * reviewed-disclosure table: `FIELDS` in `src/lumecon_data/collections/
 * foundation_release.py`, teim-team/Lumecon-data at f917e6e (branch
 * codex/foundation-corporate-giving). Copied, not invented, and only until a
 * release brings the collection's codebook table here; then that table is
 * what the questions are held to and this list goes.
 */
const PRODUCER_FIELDS = Object.freeze({
  "foundation-corporate-giving": Object.freeze([
    "disclosure_id", "award_id", "version_kind", "funder_name", "recipient_name", "cedar_uid",
    "recipient_entity_type", "recipient_affiliation", "purpose", "amount_exact_usd", "amount_lower_usd",
    "amount_upper_usd", "amount_aggregate_usd", "financial_status", "announcement_date", "report_year",
    "award_period_text", "project_geography", "source_url", "source_document_sha256",
    "source_retrieved_date", "source_class", "source_id", "publication_rights_status", "overlap_status",
    "addability_status", "observation",
  ]),
});

/** Collections with no codebook and no producer anywhere: named, and only these. */
const NO_PRODUCER = Object.freeze(["plot"]);

test("a collection with no release holds its questions to the producer's fields, or is named as having none", () => {
  assert.deepEqual([...PENDING_RELEASE].sort(), ["foundation-corporate-giving", "plot"]);
  for (const id of PENDING_RELEASE) {
    const questions = collectionQuestions(id);
    assert.ok(questions.length >= 2, `${id} has no questions`);
    if (codebookTable(id)) {
      assert.fail(`${id} has a codebook table now: move its questions into COLLECTION_JOBS and hold them to it`);
    }
    if (NO_PRODUCER.includes(id)) {
      // No producer exists, so there is nothing to name; the day one does,
      // its fields go on these questions and the id comes off NO_PRODUCER.
      assert.ok(!PRODUCER_FIELDS[id], `${id} has a producer contract: take it off NO_PRODUCER`);
      for (const item of questions) assert.deepEqual([...item.fields], [], `"${item.q}" names a field nothing declares`);
      continue;
    }
    const columns = new Set(PRODUCER_FIELDS[id] ?? []);
    assert.ok(columns.size, `${id} has neither a codebook table nor a producer contract to check against`);
    for (const item of questions) {
      assert.ok(item.fields.length, `"${item.q}" names no field`);
      for (const column of item.fields) assert.ok(columns.has(column), `"${item.q}" rests on ${column}, which the producer does not declare`);
    }
  }
});

test("every question carries a kind, and each collection mixes them", () => {
  const kinds = new Set(Object.values(QUESTION_KINDS));
  assert.deepEqual([...kinds].sort(), ["Compare", "Describe", "Trace"]);
  for (const [id, jobs] of Object.entries(ALL_COLLECTION_JOBS)) {
    for (const item of [...jobs.questions, ...(jobs.cedar ?? [])]) assert.ok(kinds.has(item.kind), `${id}: "${item.q}" has kind ${item.kind}`);
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
  for (const [id, jobs] of Object.entries(ALL_COLLECTION_JOBS)) {
    for (const item of [...jobs.questions, ...(jobs.cedar ?? [])]) {
      assert.match(item.q, /^[A-Z][^&—]*\?$/, `${id}: "${item.q}" is not one plain question`);
    }
  }
});

// ── Every audience shows the owner's sentence ──────────────────────────────

test("every collection an audience cites is in the catalog, and all eleven audiences show", () => {
  const catalogIds = liveIdsOf();
  for (const id of citedIds(ALL)) assert.ok(catalogIds.has(id), `${id} is not in the catalog`);
  const shown = visibleAudiences();
  assert.equal(shown.length, 11, "all eleven, Foundations included");
  assert.equal(shown.length, AUDIENCE_JOBS.length, "no audience is hidden");
  assert.equal(shown[5].id, "foundations-philanthropy", "in its place, after Native nonprofits");
  for (const audience of shown) {
    const declared = AUDIENCE_JOBS.find((a) => a.id === audience.id);
    assert.equal(audience.explanation, declared.explanation, audience.id);
    assert.deepEqual(audience.collections.map((entry) => entry.id), [...declared.collections], audience.id);
    assert.ok(audience.collections.length >= MIN_COLLECTIONS, `${audience.id} is too thin to show`);
  }
  assert.equal(resolveAudience({ ...AUDIENCE_JOBS[0], collections: ["funding", "deals", "gaming"] }), null, "an id nobody declared hides the audience");
});

test("the owner's launch sentences are the ones shown", () => {
  // Land in Journalists, property activity for ANCs and NHOs and for Banks,
  // and private giving for Native nonprofits: the sentences the interim copy
  // stood in for until both collections joined Cedar Press.
  const byId = Object.fromEntries(visibleAudiences().map((a) => [a.id, a]));
  const ids = (audience) => audience.collections.map((entry) => entry.id);
  assert.match(byId.journalists.explanation, /ownership, land and transactions/);
  assert.ok(ids(byId.journalists).includes("plot"));
  for (const id of ["ancs-nhos", "banks-lenders"]) {
    assert.match(byId[id].explanation, /property activity/, id);
    assert.ok(ids(byId[id]).includes("plot"), id);
  }
  assert.match(byId["native-nonprofits"].explanation, /combine federal and private support/);
  assert.ok(ids(byId["native-nonprofits"]).includes("foundation-corporate-giving"));
  assert.deepEqual(ids(byId["foundations-philanthropy"]), ["foundation-corporate-giving", "funding", "nonprofits"]);
});

test("Foundations and philanthropy says that it is not a need score", () => {
  // The owner's caution: observable indicators of funding and activity, never
  // a definitive need score.
  const foundations = AUDIENCE_JOBS.find((audience) => audience.id === "foundations-philanthropy");
  assert.match(foundations.explanation, /not a need score/);
  // And nowhere else does it claim to measure need.
  const rest = `${foundations.outcome} ${foundations.explanation}`.replace(/not a need score/g, "");
  assert.doesNotMatch(rest, /need score|scores? (of|for) need|need index|rank\w* need|most in need/i);
});

test("an audience with fewer than three live collections is hidden rather than shown thin", () => {
  const thin = { id: "thin", audience: "Thin", job: "Research", outcome: "x", explanation: "x", collections: ["funding", "deals"] };
  assert.equal(resolveAudience(thin), null);
});

// ── Coverage: a report for review, not a rule ─────────────────────────────

test("coverage report: live collections no shown use case names", (t) => {
  // Owner, 2026-09-26: "The landing page should show the best reasons to use
  // Cedar Press, not prove that each dataset got a turn." So this reports and
  // never fails; docs/DESIGN_SYSTEM.md carries the same list for review.
  const today = uncoveredIds();
  t.diagnostic(`uncovered: ${today.length ? today.join(", ") : "none"}`);
});

test("the coverage report names a collection that loses its last use case", () => {
  // The report's mechanism, not a coverage rule: it has to be able to see a gap.
  assert.ok(!uncoveredIds().includes("nagpra"));
  const withoutNagpra = AUDIENCE_JOBS.map((audience) => ({
    ...audience,
    collections: audience.collections.map((id) => (id === "nagpra" ? "funding" : id)),
  }));
  assert.ok(uncoveredIds(STOREFRONT_CATALOG, withoutNagpra).includes("nagpra"));
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
    assert.doesNotMatch(audience.explanation, /[—&]/, `${audience.id}: no em dash, no ampersand`);
    assert.doesNotMatch(audience.explanation, /\bimpact\b/i, `${audience.id}: "contribution", not "impact"`);
    assert.match(audience.explanation, /^[A-Z].*\.$/, `${audience.id}: complete sentences`);
    assert.ok(audience.collections.length >= MIN_COLLECTIONS && audience.collections.length <= 6, audience.id);
  }
  for (const line of [BAND_NOTE, ENTITY_JOBS.line]) assert.match(line, /^[A-Z][^&—]*\.$/, line);
});

test("the layer names collections by id only: no second catalog", () => {
  const catalogIds = new Set(PRESS_CATALOG.map((entry) => entry.id));
  for (const id of citedIds(ALL)) assert.ok(catalogIds.has(id), id);
  for (const file of ["./pressJobs.js"]) {
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
  const missing = [{ id: "x", researchExample: { text: "Gaming only.", collections: ["gaming"] } }];
  assert.deepEqual(researchExamples(STOREFRONT_CATALOG, missing), [], "an example citing a collection not in the catalog is not offered");
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

test("every collection has a mark, and the two new marks are drawn with the family", () => {
  const family = read("../../pages/grove/pressCollectionIcons.jsx");
  const keyedIn = (src, id) =>
    new RegExp(`(^|\\s)(${id}|"${id}"):\\s*\\w+Icon,`, "m").test(src.slice(src.search(/export const \w+_ICONS/)));
  for (const entry of STOREFRONT_CATALOG) assert.ok(keyedIn(family, entry.id), `no mark for ${entry.id}`);
  for (const name of ["GivingIcon", "PlotIcon"]) {
    const start = family.indexOf(`const ${name} = (`);
    assert.ok(start >= 0, name);
    const body = family.slice(start, family.indexOf(");", start));
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
  assert.match(catalogDescription(), /^Fourteen collections on Indian Country's economy: federal funding, /);
  assert.match(catalogDescription(), /foundation and corporate giving/);
  assert.match(catalogDescription(), /PLOT parcel records/);
  assert.match(catalogDescription(STOREFRONT_CATALOG.slice(0, 3)), /^Three collections on /);
  assert.throws(() => catalogDescription([{ id: "not-a-collection" }]), /no catalog phrase for not-a-collection/, "a collection with no phrase stops the generator by name");
});

test("the fourteen split seven and seven: giving in Cedar Press, PLOT in Cedar Press+", () => {
  const shelves = (catalog) => ({
    standard: catalog.filter((entry) => entry.shelf === "standard").length,
    pro: catalog.filter((entry) => entry.shelf === "pro").length,
  });
  assert.equal(STOREFRONT_CATALOG.length, 14);
  assert.deepEqual(shelves(STOREFRONT_CATALOG), { standard: 7, pro: 7 });
  const byId = Object.fromEntries(STOREFRONT_CATALOG.map((entry) => [entry.id, entry]));
  assert.equal(byId["foundation-corporate-giving"].shelf, "standard");
  assert.equal(byId.plot.shelf, "pro");
  // The owner's Methods concepts are each collection's linkage line.
  assert.match(byId["foundation-corporate-giving"].linkage, /^Philanthropic, corporate and bank giving/);
  assert.match(byId.plot.linkage, /^Land ownership, transfers, permitting and development/);
});

test("the owner's cross-collection examples for the two new collections are in Methods", () => {
  const deals = ECOSYSTEM_EXAMPLES.find((text) => text.includes("PLOT"));
  assert.match(deals, /Indian Country Deals links to the parcels PLOT follows/);
  const giving = ECOSYSTEM_EXAMPLES.find((text) => text.startsWith("Foundation, corporate and bank giving"));
  assert.match(giving, /federal funding and the Native Nonprofits roster/);
});

test("the time-savings sentence appears exactly once, on Research access", () => {
  const sentence = "Lumecon maintains the source trail, entity relationships and releases behind these records";
  const where = runtimeSources().filter(({ text }) => flat(text).includes(sentence)).map(({ rel }) => rel);
  assert.deepEqual(where, ["pages/grove/CedarPressResearchAccess.jsx"]);
});

test("Priorities asks what should exist next: examples, ambitious, and nothing Cedar Press already carries", () => {
  const { datasets, research, expansions } = PRIORITY_EXAMPLES;
  assert.deepEqual(datasets.map((d) => d.theme), ["Infrastructure", "Capital access", "Housing", "Healthcare", "Energy", "Workforce"]);
  assert.ok(research.descriptive.length >= 2 && research.causal.length >= 2);
  assert.ok(expansions.length >= 2 && expansions.length < datasets.length, "the narrower asks stay the smaller set");
  const all = [...datasets.map((d) => d.text), ...research.descriptive, ...research.causal, ...expansions];
  for (const text of all) {
    assert.doesNotMatch(text, /[&\u2014]/, text);
    assert.doesNotMatch(text, /\bimpact\b/i, text);
    assert.doesNotMatch(text, /parcel|permit|land ownership|philanthrop|foundation|corporate giving|PLOT/i, `${text}: asks for a collection Cedar Press already carries`);
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
