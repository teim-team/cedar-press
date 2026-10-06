import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { buildArticlePdf, pdfFileName, pdfText, shareEmail } from "./articlePdf.js";
import { TBN_PLANS_URL } from "./pressArticles.js";

const SERVER_ARTICLES = JSON.parse(readFileSync(new URL("../../../server/cedar_press/articles.json", import.meta.url), "utf8"));
const hosted = SERVER_ARTICLES.filter((a) => a.hosted);

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


test("nonnumeric evidence PDFs retain every role, event, detail and source link", async () => {
  const { jsPDF } = await import("jspdf");
  function UncompressedPdf(options) { return new jsPDF({ ...options, compress: false }); }
  const sources = [{ title: "Evidence announcement", url: "https://example.org/announcement" }];
  const base = { kind: "figure", caption: "Evidence fixture", source: "Owner announcement",
    notes: ["Reported roles are dated.", "No ownership share inferred."], sources };
  const article = { ...hosted[0], title: "Evidence PDF fixture", body: [
    { ...base, chart: "relationships", relationships: [
      { from: "PDFGOVERNMENT", relationship: "owns", to: "PDFENTERPRISE", asOf: "2020-01-15", detail: "PDFRELATIONDETAIL", sources },
    ] },
    { ...base, chart: "timeline", events: [
      { date: "2022-03-14", title: "PDFEVENT", detail: "PDFEVENTDETAIL", sources },
    ] },
    { ...base, chart: "evidenceTable", rows: [
      { entity: "PDFMANAGER", role: "PDFROLE", asOf: "2022-03-14", detail: "PDFROLEDETAIL", sources },
    ], columns: [{ key: "entity", label: "Organization" }] },
  ] };
  const blob = await buildArticlePdf({ article, url: "https://cedarpress.ai/articles/evidence", jsPDF: UncompressedPdf });
  const raw = new TextDecoder("latin1").decode(await blob.arrayBuffer());
  for (const text of ["PDFGOVERNMENT", "PDFENTERPRISE", "PDFRELATIONDETAIL", "PDFEVENT",
    "PDFEVENTDETAIL", "PDFMANAGER", "PDFROLE", "PDFROLEDETAIL", "2020-01-15", "2022-03-14",
    "https://example.org/announcement"]) assert.ok(raw.includes(text), text);
});
