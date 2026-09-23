// The Methods page's shape, held against its source.
//
// Two things went wrong on desktop and neither was visible in a unit test of
// the copy: the chapter index was a floated sticky block that slid down over
// the chapter text as the page scrolled, and the ecosystem ring was folded
// inside a closed disclosure at a width it could never be read at. These
// read the page and the stylesheet, so the fixes cannot drift back quietly.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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
  // A third of the page on desktop, first on a phone.
  const lead2 = rulesFor("cp-meth__lead").find((block) => /grid-template-columns\s*:\s*minmax\(0, 1\.5fr\) minmax\(0, 1fr\)/.test(block.body));
  assert.ok(lead2, "the lead does not give the ring a third of the width");
  const stacked = rulesFor("cp-eco").find((block) => /order\s*:\s*-1/.test(block.body));
  assert.ok(stacked, "the ring does not stack first on a phone");
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
