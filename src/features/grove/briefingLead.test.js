/**
 * The front page dropped the lead's picture, and nothing noticed for as long
 * as the page existed. It was measurably the thinnest page in the product —
 * 275 words and one image, that image being the masthead logo — while being
 * the first screen a subscriber sees after signing in.
 *
 * Nothing failed, because "renders fewer elements than it could" is not a
 * test failure. So the parity is asserted directly: the same article object
 * feeds both surfaces, and both must use it the same way.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ARTICLE_IMAGE, PRESS_ARTICLES } from "./pressArticles.js";

const read = (rel) => readFileSync(new URL(rel, import.meta.url), "utf8");
const briefing = () => read("../../pages/grove/PressBriefing.jsx");
const articles = () => read("../../pages/grove/CedarPressArticles.jsx");

test("the lead article actually carries an image to render", () => {
  const [lead] = PRESS_ARTICLES;
  assert.ok(lead, "there must be a lead article");
  assert.match(lead.image, /^\/.+\.(webp|png|jpg|jpeg)$/, "the lead needs a real image path");
  assert.ok(typeof lead.imageAlt === "string" && lead.imageAlt.length > 0, "alt text is not optional");
});

test("every article carries an image, so the briefing can always show one", () => {
  // If this ever stops being true the briefing's `lead.image ?` guard is what
  // keeps the page rendering, and this test is what says the guard started
  // doing something rather than sitting there dead.
  const missing = PRESS_ARTICLES.filter((a) => !a.image).map((a) => a.id);
  assert.deepEqual(missing, [], "articles without an image would render a textless lead");
});

test("the briefing renders the lead's image", () => {
  const src = briefing();
  assert.match(src, /lead\.image/, "the briefing must read the lead's image");
  assert.match(src, /src=\{lead\.image\}/, "and render it, not merely test it");
  assert.match(src, /alt=\{lead\.imageAlt\}/, "with the article's own alt text");
});

test("both surfaces size the image from one constant, so they cannot drift", () => {
  for (const [name, src] of [["the briefing", briefing()], ["the articles index", articles()]]) {
    assert.match(src, /ARTICLE_IMAGE\.width/, `${name} must take its width from ARTICLE_IMAGE`);
    assert.match(src, /ARTICLE_IMAGE\.height/, `${name} must take its height from ARTICLE_IMAGE`);
  }
  assert.ok(ARTICLE_IMAGE.width > 0 && ARTICLE_IMAGE.height > 0);
});

test("the intrinsic ratio and the CSS aspect-ratio agree", () => {
  // A mismatch here is the bug this guards against: the box is reserved at
  // one ratio and the file arrives at another, so the headline jumps.
  const css = read("../../styles/grove/press.css");
  const rule = css.match(/\.cp-brief__img\s*\{[^}]*aspect-ratio:\s*(\d+)\s*\/\s*(\d+)/);
  assert.ok(rule, "the lead image needs a declared aspect-ratio");
  assert.equal(Number(rule[1]), ARTICLE_IMAGE.width, "CSS width must match the intrinsic width");
  assert.equal(Number(rule[2]), ARTICLE_IMAGE.height, "CSS height must match the intrinsic height");
});
