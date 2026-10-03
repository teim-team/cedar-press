// Cedar Press articles: one per launch dataset, each naming a dataset the
// page actually shows. The card artwork is the dataset's figure, so a broken
// datasetId would render an empty card; this pins the join.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { COLLECTION_FIGURES, LAUNCH_COLLECTION } from "./collection.js";
import { BLOCK, PRESS_ARTICLES as PUBLIC_ARTICLES } from "./pressArticles.js";
import { CHART_RULES, figureProblems } from "./pressCharts.js";
import { PRESS_CATALOG_BY_ID } from "./pressCatalog.js";

const SERVER_ARTICLES = JSON.parse(readFileSync(new URL("../../../server/cedar_press/articles.json", import.meta.url), "utf8"));
const PRESS_ARTICLES = SERVER_ARTICLES.filter((article) => article.id.startsWith("brief-"));

test("every article draws from a real dataset with a real figure", () => {
  for (const article of PRESS_ARTICLES) {
    assert.ok(LAUNCH_COLLECTION.some((d) => d.id === article.datasetId), article.id);
    assert.ok(COLLECTION_FIGURES.some((f) => f.id === article.datasetId), article.id);
    assert.ok(article.title && article.dek && article.date, article.id);
  }
});

// This was "every launch dataset has an article slot filled", and it held
// while the shelf was the four pilot datasets. The shelf is twelve now, and
// there are still four articles: the eight collections that arrived with the
// real descriptors have no Research Brief written about them, and writing eight to
// turn this green would be inventing the product's editorial output.
//
// So the invariant is stated as the fact it actually is: THESE datasets have
// an article, and the rest are a named gap. Losing an article still fails, and
// so does adding one without listing it, which is what the old assertion
// protected. What it no longer does is claim coverage the page does not have.
const DATASETS_WITH_AN_ARTICLE = ["owned", "deals", "contractors", "funding"];

test("the datasets with a Research Brief are exactly the ones listed", () => {
  const written = [...new Set(PRESS_ARTICLES.map((a) => a.datasetId))].sort();
  assert.deepEqual(written, [...DATASETS_WITH_AN_ARTICLE].sort());
});

test("every dataset named as having an article is on the shelf", () => {
  for (const id of DATASETS_WITH_AN_ARTICLE) {
    assert.ok(LAUNCH_COLLECTION.some((d) => d.id === id), `${id} is not on the shelf`);
  }
});

// A piece lives in exactly one place. Hosted means it opens on Cedar Press and
// carries a body; anything else opens on Tribal Business News and needs a URL
// to open. Half of either shape renders a card that goes nowhere.
test("every article is either hosted with a body or external with a URL", () => {
  for (const article of PRESS_ARTICLES) {
    if (article.hosted) {
      assert.ok(Array.isArray(article.body) && article.body.length, `${article.id} has no body`);
      assert.ok(article.byline, `${article.id} has no byline`);
      assert.equal(article.href, undefined, `${article.id} is hosted and still has an href`);
    } else {
      assert.ok(article.href, `${article.id} is external and has no URL`);
      assert.equal(article.body, undefined, `${article.id} is external and carries a body`);
    }
  }
});

test("a hosted body only contains blocks the page can render", () => {
  const kinds = new Set(Object.values(BLOCK));
  for (const article of PRESS_ARTICLES.filter((a) => a.hosted)) {
    for (const block of article.body) {
      assert.ok(kinds.has(block.kind), `${article.id}: ${block.kind}`);
      if (block.kind === BLOCK.FIGURE) {
        assert.deepEqual(
          figureProblems({ ...block, kind: block.chart }),
          [],
          `${article.id}: figure is not publishable`,
        );
        assert.ok(PRESS_CATALOG_BY_ID[block.source], `${article.id}: figure names ${block.source}, which is not a collection`);
      } else if (block.kind === BLOCK.IMAGE) {
        assert.ok(block.src && block.alt && block.caption, `${article.id}: image is missing a source, alt text or caption`);
      } else if (block.kind === BLOCK.PAIR) {
        assert.equal(block.images.length, 2, `${article.id}: a pair is two pictures`);
        for (const image of block.images) {
          assert.ok(image.src && image.alt && image.caption, `${article.id}: paired image is incomplete`);
        }
      } else {
        assert.ok(block.text, `${article.id}: empty ${block.kind}`);
      }
    }
  }
});

// The upgrade path only works if the collections a piece declares are real
// ones, since the page resolves each against the reader's entitlement.
test("every collection an article draws on is in the catalog", () => {
  for (const article of PRESS_ARTICLES.filter((a) => a.hosted)) {
    for (const id of article.draws ?? [article.datasetId]) {
      assert.ok(PRESS_CATALOG_BY_ID[id], `${article.id} draws on ${id}`);
    }
  }
});

// The layout is designed for two or three pictures, so a piece that ships one
// is a piece nobody laid out. The lead counts as the first.
test("a hosted piece carries two or three photographs", () => {
  for (const article of PRESS_ARTICLES.filter((a) => a.hosted)) {
    const inBody = article.body.reduce(
      (n, b) => n + (b.kind === BLOCK.IMAGE ? 1 : b.kind === BLOCK.PAIR ? b.images.length : 0),
      0,
    );
    const total = (article.image ? 1 : 0) + inBody;
    assert.ok(total >= 2 && total <= 3, `${article.id} has ${total}`);
  }
});

// Alt text is not the caption. One describes the picture for somebody who
// cannot see it and the other says what it means, and using either for both
// leaves one job undone.
test("every picture has alt text distinct from its caption", () => {
  for (const article of PRESS_ARTICLES.filter((a) => a.hosted)) {
    const images = [
      { alt: article.imageAlt, caption: article.caption },
      ...article.body.filter((b) => b.kind === BLOCK.IMAGE),
      ...article.body.filter((b) => b.kind === BLOCK.PAIR).flatMap((b) => b.images),
    ];
    for (const image of images) {
      assert.ok(image.alt, `${article.id}: a picture has no alt text`);
      assert.notEqual(image.alt, image.caption, `${article.id}: alt text is doing duty as a caption`);
    }
  }
});

// A chart is a claim, and a claim without its assumptions is an assertion.
// The notes are where a reader finds what is counted, what is excluded and
// which choices changed the shape.
test("every figure states its assumptions under the chart", () => {
  let figures = 0;
  for (const article of PRESS_ARTICLES.filter((a) => a.hosted)) {
    for (const block of article.body.filter((b) => b.kind === BLOCK.FIGURE)) {
      figures += 1;
      assert.ok(block.notes.length >= 2, `${article.id}: ${block.chart} has ${block.notes.length} note(s)`);
      for (const note of block.notes) {
        assert.ok(note.trim().length > 20, `${article.id}: a note says nothing`);
      }
    }
  }
  // If every hosted article drops its figures, the loops above assert nothing
  // and this test goes green on air. Demand it saw at least one figure.
  assert.ok(figures > 0, "no hosted figures were checked, so nothing was enforced");
});

// The marks an article uses have to be marks somebody wrote a rule for, or
// the vocabulary is whatever the last editor felt like.
test("every mark used has a rule, and every rule says when not to use it", () => {
  const kinds = new Set(CHART_RULES.map((r) => r.kind));
  for (const article of PRESS_ARTICLES.filter((a) => a.hosted)) {
    for (const block of article.body.filter((b) => b.kind === BLOCK.FIGURE)) {
      assert.ok(kinds.has(block.chart), `${article.id}: ${block.chart} has no rule`);
    }
  }
  for (const rule of CHART_RULES) {
    assert.ok(rule.use.length > 30, `${rule.kind}: no guidance on when to use it`);
    assert.ok(rule.avoid.length > 30, `${rule.kind}: no guidance on when not to`);
    assert.ok(rule.axis.length > 20, `${rule.kind}: nothing about its axis`);
  }
});

test("public cards never carry subscriber bodies or highlights", () => {
  const publicSource = readFileSync(new URL("./pressArticles.js", import.meta.url), "utf8");
  for (const article of PUBLIC_ARTICLES) {
    assert.equal(article.body, undefined);
    assert.equal(article.highlights, undefined);
  }
  for (const article of SERVER_ARTICLES.filter((a) => a.hosted)) {
    for (const block of article.body.filter((b) => b.kind === BLOCK.P)) {
      assert.ok(!publicSource.includes(block.text), article.id);
    }
  }
});

test("new server drafts have renderable bodies and an explicit preliminary status", () => {
  const ids = new Set();
  for (const article of SERVER_ARTICLES) {
    assert.ok(!ids.has(article.id), article.id);
    ids.add(article.id);
    if (article.id.startsWith("brief-")) continue;
    assert.equal(article.earlyAccess, true);
    assert.equal(article.draft, true);
    assert.ok(article.title && article.byline && article.body.length);
    assert.equal(article.highlights.length, 3);
    for (const block of article.body) {
      assert.ok(Object.values(BLOCK).includes(block.kind));
      if (block.kind === BLOCK.FIGURE) {
        assert.deepEqual(figureProblems({ ...block, kind: block.chart }), []);
      }
    }
  }
});


function evidenceFixture(kind) {
  const sources = [{ url: "https://example.org/announcement", title: "Owner announcement" }];
  const base = { kind, id: "test-evidence", caption: "Documented roles", source: "Owner announcement",
    notes: ["Roles are dated.", "Ownership shares are not inferred."], sources };
  if (kind === "relationships") return { ...base, relationships: [
    { from: "Government", relationship: "owns", to: "Enterprise", asOf: "2020-01-15", detail: "An explicit relationship.", sources },
  ] };
  if (kind === "timeline") return { ...base, events: [
    { date: "2022-03-14", title: "Branding update", detail: "Not another purchase.", sources },
  ] };
  return { ...base, columns: [{ key: "entity", label: "Organization" }, { key: "role", label: "Reported role" }],
    rows: [{ entity: "Manager", role: "Property manager", asOf: "2022-03-14", detail: "Management does not establish ownership.", sources }] };
}

test("sourced nonnumeric figures preserve relationships, event dates and reported roles", () => {
  for (const kind of ["relationships", "timeline", "evidenceTable"]) {
    assert.deepEqual(figureProblems(evidenceFixture(kind)), []);
  }
});

test("evidence figures reject missing observations, fabricated magnitudes and invalid dates", () => {
  for (const kind of ["relationships", "timeline", "evidenceTable"]) {
    const fixture = evidenceFixture(kind);
    const key = { relationships: "relationships", timeline: "events", evidenceTable: "rows" }[kind];
    assert.ok(figureProblems({ ...fixture, [key]: [] }).length);
    assert.ok(figureProblems({ ...fixture, points: [{ label: "Invented", value: 1 }] }).length);
    assert.ok(figureProblems({ ...fixture, [key]: [{ ...fixture[key][0], sources: [] }] }).length);
    assert.ok(figureProblems({ ...fixture, [key]: [{ ...fixture[key][0], detail: {} }] }).length);
    const dateKey = kind === "timeline" ? "date" : "asOf";
    assert.ok(figureProblems({ ...fixture, [key]: [{ ...fixture[key][0], [dateKey]: "2022-02-30" }] }).length);
  }
  const table = evidenceFixture("evidenceTable");
  assert.ok(figureProblems({ ...table, columns: [{ key: "__proto__", label: "Private" }] }).length);
  assert.ok(figureProblems({ ...table, columns: [table.columns[0], table.columns[0]] }).length);
  assert.ok(figureProblems({ ...table, sources: [{ url: "file:///private" }] }).length);
});
