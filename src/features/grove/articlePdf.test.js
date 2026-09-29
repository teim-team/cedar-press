import assert from "node:assert/strict";
import test from "node:test";

import { buildArticlePdf, pdfFileName, pdfText, shareEmail } from "./articlePdf.js";
import { PRESS_ARTICLES, TBN_PLANS_URL } from "./pressArticles.js";

const hosted = PRESS_ARTICLES.filter((a) => a.hosted);

test("text outside the standard fonts is dropped, not printed as a wrong glyph", () => {
  assert.equal(pdfText("Open the data →"), "Open the data");
  assert.equal(pdfText("5 − 3"), "5 - 3");
  assert.equal(pdfText("Nation’s “first” · 2026"), "Nation’s “first” · 2026");
});

test("the file is named for the brief", () => {
  assert.equal(pdfFileName({ title: "Announced deals: Q2, 2026!" }), "announced-deals-q2-2026.pdf");
  assert.equal(pdfFileName({}), "cedar-press-brief.pdf");
});

test("the share email names the brief, links it, and says how to get Cedar Press+", () => {
  const { subject, body, href } = shareEmail(hosted[0], "https://cedarpress.ai/articles/x");
  assert.match(subject, /^Cedar Press: /);
  assert.ok(body.includes("https://cedarpress.ai/articles/x"));
  assert.ok(body.includes(TBN_PLANS_URL));
  assert.ok(href.startsWith("mailto:?subject="));
  assert.doesNotMatch(body, /\p{Extended_Pictographic}/u);
});

test("every hosted brief builds a PDF", async () => {
  for (const article of hosted) {
    const blob = await buildArticlePdf({
      article,
      url: `https://cedarpress.ai/articles/${article.id}`,
      collections: [{ name: "Indian Country Deals", href: "https://cedarpress.ai/data?c=deals" }],
    });
    const bytes = new Uint8Array(await blob.arrayBuffer());
    assert.equal(new TextDecoder().decode(bytes.slice(0, 5)), "%PDF-", article.id);
    assert.ok(bytes.length > 3000, `${article.id}: ${bytes.length} bytes`);
    // The subscribe link is a real link annotation, not just text.
    const raw = new TextDecoder("latin1").decode(bytes);
    assert.ok(raw.includes(TBN_PLANS_URL), `${article.id} does not link Cedar Press+`);
  }
});
