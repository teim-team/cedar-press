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

/**
 * Source with its comments removed.
 *
 * Codex, on the first version of this file: a regex over raw source still
 * matches when the JSX it is looking for has been commented out, so the
 * regression these tests exist to catch would pass them. That is the same
 * fault `deployGates.test.js` was written to avoid -- a check that stops
 * checking without ever failing -- so the comments come out before anything
 * is matched, and `rendersTheImage` below is pinned against fixtures that
 * prove it.
 *
 * The rendered assertion lives in the smoke suite, on `.cp-brief__img` and
 * its `naturalWidth`, because only a browser can say the file arrived.
 */
export function code(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^[ \t]*\/\/.*$/gm, "");
}

/** Whether a source really renders the lead's image, comments excluded. */
export function rendersTheImage(source) {
  const bare = code(source);
  return /src=\{lead\.image\}/.test(bare) && /alt=\{lead\.imageAlt\}/.test(bare);
}

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
  assert.ok(rendersTheImage(briefing()), "the briefing must render the lead's image");
});

test("a commented-out image does NOT count as rendering it", () => {
  // The negative fixture Codex asked for. Both shapes below would satisfy a
  // regex over raw source, and neither puts a pixel on the page.
  const blockComment = `
    {/* <img src={lead.image} alt={lead.imageAlt} /> */}
    <h2>{lead.title}</h2>`;
  const lineComment = `
    // <img src={lead.image} alt={lead.imageAlt} />
    <h2>{lead.title}</h2>`;
  assert.equal(rendersTheImage(blockComment), false, "a block-commented image is not rendered");
  assert.equal(rendersTheImage(lineComment), false, "a line-commented image is not rendered");
});

test("the reader still sees a real, uncommented image", () => {
  const live = `
    {lead.image ? <img src={lead.image} alt={lead.imageAlt} /> : null}`;
  assert.equal(rendersTheImage(live), true);
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
  //
  // Codex: compare the RATIO, not the raw numbers. Reprocessing the
  // photography to 750x300 would require ARTICLE_IMAGE to change so the
  // intrinsic sizing stays truthful, while `1500 / 600` remains the same
  // correct ratio -- and a raw-number check would fail CI over a box that
  // did not move. Cross-multiplied, so there is no float division.
  const css = read("../../styles/grove/press.css");
  const rule = css.match(/\.cp-brief__img\s*\{[^}]*aspect-ratio:\s*(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)/);
  assert.ok(rule, "the lead image needs a declared aspect-ratio");
  const [cssW, cssH] = [Number(rule[1]), Number(rule[2])];
  assert.equal(
    cssW * ARTICLE_IMAGE.height,
    cssH * ARTICLE_IMAGE.width,
    `CSS ${cssW}/${cssH} is a different shape from the intrinsic ${ARTICLE_IMAGE.width}x${ARTICLE_IMAGE.height}`,
  );
});

test("an equivalent ratio expressed differently is accepted", () => {
  // 750/300 and 1500/600 are the same box. The guard must not care.
  const equivalent = (w, h) => w * ARTICLE_IMAGE.height === h * ARTICLE_IMAGE.width;
  assert.ok(equivalent(ARTICLE_IMAGE.width / 2, ARTICLE_IMAGE.height / 2), "half-size is the same shape");
  assert.ok(equivalent(ARTICLE_IMAGE.width * 2, ARTICLE_IMAGE.height * 2), "double is the same shape");
  assert.ok(!equivalent(ARTICLE_IMAGE.width, ARTICLE_IMAGE.height + 1), "a real change is still caught");
});
