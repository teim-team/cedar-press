// The Methods page's shape, held against its source.
//
// Two things went wrong on desktop and neither was visible in a unit test of
// the copy: the chapter index was a floated sticky block that slid down over
// the chapter text as the page scrolled, and the ecosystem ring was folded
// inside a closed disclosure at a width it could never be read at. These
// read the page and the stylesheet, so the fixes cannot drift back quietly.

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import test from "node:test";

const PAGE = readFileSync(new URL("../../pages/grove/CedarPressMethods.jsx", import.meta.url), "utf8");
const CSS = readFileSync(new URL("../../styles/grove/press.css", import.meta.url), "utf8");

/** The declaration blocks whose selector carries the class as an exact token. */
function rulesFor(className) {
  const stripped = CSS.replace(/\/\*[\s\S]*?\*\//g, "");
  const token = new RegExp(`\\.${className.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\w-])`);
  const blocks = [];
  for (const match of stripped.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (token.test(match[1])) blocks.push({ selector: match[1].trim(), body: match[2] });
  }
  return blocks;
}

test("the index is a column of a grid, never a float", () => {
  for (const block of rulesFor("cp-mix")) {
    assert.doesNotMatch(block.body, /float\s*:/, `${block.selector} floats the index`);
  }
  const grid = rulesFor("cp-meth__grid").find((block) => /display\s*:\s*grid/.test(block.body));
  assert.ok(grid, "no grid rule for the Methods page");
  assert.match(grid.body, /grid-template-columns\s*:\s*14rem/);
  assert.match(PAGE, /<div className="cp-meth__grid">\s*<MethodsIndex \/>\s*<div className="cp-meth__body">/);
});

test("the ring is the first chapter's figure, beside the text and outside any disclosure", () => {
  const figure = PAGE.indexOf("<EcosystemDiagram />");
  assert.ok(figure > 0, "the ring is not rendered");
  const firstReasoning = PAGE.indexOf("<Reasoning label=");
  assert.ok(firstReasoning > figure, "the ring is inside or below a folded disclosure");
  const lead = PAGE.indexOf('className="cp-meth__lead"');
  assert.ok(lead > 0 && lead < figure, "the ring is not in the chapter's lead");
  const chapter = PAGE.indexOf('id="collections"');
  assert.ok(chapter > 0 && chapter < figure, "the ring is not in the first chapter");
  // Left of the text on desktop, where the fixed Ask Cedar launcher (lower
  // right) cannot reach it, and never narrower than 25rem, where its 22px
  // canvas labels still render above 11px. First on a phone too.
  const lead2 = rulesFor("cp-meth__lead").find((block) => /grid-template-columns\s*:\s*minmax\(25rem, 1fr\) minmax\(0, 1\.2fr\)/.test(block.body));
  assert.ok(lead2, "the lead does not give the ring the left column with a 25rem floor");
  const stacked = rulesFor("cp-eco").find((block) => /order\s*:\s*-1/.test(block.body));
  assert.ok(stacked, "the ring does not come first");
  for (const block of rulesFor("cp-eco")) {
    assert.doesNotMatch(block.body, /order\s*:\s*0\b/, `${block.selector} moves the ring after the text`);
  }
  for (const block of rulesFor("cp-meth__lead")) {
    assert.doesNotMatch(block.body, /padding-right/, `${block.selector} reserves dead space instead of moving the ring`);
  }
  // Drawn on every width: the phone form no longer hides the figure.
  for (const block of rulesFor("cp-eco__figure")) {
    assert.doesNotMatch(block.body, /display\s*:\s*none/, `${block.selector} hides the ring`);
  }
});

test("five chapters, in the order a reader trusts a figure", () => {
  const ids = [...PAGE.matchAll(/\{ id: "([a-z]+)", label: "[^"]+", icon: \w+ \}/g)].map((m) => m[1]);
  assert.deepEqual(ids, ["collections", "records", "limits", "cite", "team"]);
  for (const id of ids) assert.match(PAGE, new RegExp(`<Chapter\\s+id="${id}"`), `chapter ${id} is not rendered`);
});

test("the citation chapter prints the form every record page and download use", () => {
  assert.match(PAGE, /import \{ collectionCitation \} from "\.\.\/\.\.\/features\/grove\/collection"/);
  assert.match(PAGE, /collectionCitation\(entry\.id, accessed\)/);
  assert.match(PAGE, /href=\{REPORT_CITATION_HREF\}/);
  assert.match(PAGE, /to=\{PRESS_WHATS_NEW_PATH\}/);
});

// Every link into the Methods page names a chapter that exists. The chapters
// were renumbered and renamed in this rebuild, and the record page's "How
// Cedar matches records" still pointed at the old `m-linkage`, which landed
// a reader at the top of the page with no sign of what they had asked for.
test("every /methods# anchor referenced from a page is a chapter on the Methods page", () => {
  const chapters = [...PAGE.matchAll(/\{ id: "([a-z]+)", label: "[^"]+", icon: \w+ \}/g)].map((m) => `m-${m[1]}`);
  assert.ok(chapters.length >= 5);
  const pages = new URL("../../pages/grove/", import.meta.url);
  const referenced = [];
  for (const name of readdirSync(pages)) {
    if (!/\.jsx?$/.test(name) || /\.test\./.test(name)) continue;
    const source = readFileSync(new URL(name, pages), "utf8");
    for (const match of source.matchAll(/(?:PRESS_METHODS_PATH\}|\/methods)#([a-z-]+)/g)) {
      referenced.push({ name, anchor: match[1] });
    }
  }
  assert.ok(referenced.some((ref) => ref.name === "CedarPressRecord.jsx"), "the record page links into Methods");
  for (const ref of referenced) {
    assert.ok(chapters.includes(ref.anchor), `${ref.name} links to #${ref.anchor}, which is not a chapter (${chapters.join(", ")})`);
  }
});
