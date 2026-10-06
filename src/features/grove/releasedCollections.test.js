import assert from "node:assert/strict";
import test from "node:test";
import { jsx } from "react/jsx-runtime";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

test("PLOT preview renders cited geometry with its exact release and no ownership implication", async () => {
  const vite = await createServer({ appType: "custom", logLevel: "silent", server: { middlewareMode: true } });
  try {
    const { PlotGeometryPreview } = await vite.ssrLoadModule("/src/pages/grove/ReleasedCollections.jsx");
    const packet = { collection: "plot", release_id: "a".repeat(64), map_preview: {
      release_id: "a".repeat(64), features: [{}], omitted: [{}], outlines: [{
        id: "plot-1", path: "M0 0 L1 0 L1 -1 Z", view_box: "0 -1 1 1", bbox: [0, 0, 1, 1],
        source: { publisher: "Bureau of Indian Affairs", url: "https://www.bia.gov/" },
      }],
    } };
    const html = renderToStaticMarkup(jsx(PlotGeometryPreview, { packet }));
    for (const value of ["Source geometry plot-1", "sizes cannot be compared", "do not certify ownership or title", "Bureau of Indian Affairs", "https://www.bia.gov/"])
      assert.ok(html.includes(value), value);
    for (const change of [{ release_id: "b".repeat(64) }, { collection: "gaming" }, { map_preview: null }])
      assert.equal(renderToStaticMarkup(jsx(PlotGeometryPreview, { packet: { ...packet, ...change } })), "");
  } finally { await vite.close(); }
});


test("the spreadsheet download requires matching verified metadata", async () => {
  const { spreadsheetDownloadUrl } = await import("../../api.js");
  const pin = "a".repeat(64);
  const meta = { kind: "spreadsheet", format: "csv", release_id: pin };
  const parts = [{ available: true, releaseId: pin }];
  assert.equal(spreadsheetDownloadUrl("plot", meta, parts), `/press/collections/plot/spreadsheet-download?release_id=${pin}`);
  assert.equal(spreadsheetDownloadUrl("plot", { ...meta, release_id: "b".repeat(64) }, parts), null);
  assert.equal(spreadsheetDownloadUrl("plot", meta, []), null);
  assert.equal(spreadsheetDownloadUrl("gaming", meta, parts), null);
  assert.equal(spreadsheetDownloadUrl("../plot", meta, parts), null);
});

test("research examples omit retired entity IDs while keeping names and source record IDs", async () => {
  const vite = await createServer({ appType: "custom", logLevel: "silent", server: { middlewareMode: true } });
  try {
    const { ResearchPreview } = await vite.ssrLoadModule("/src/pages/grove/ReleasedCollections.jsx");
    const names = ["canonical_name", "award_id", "cicd_id", "owner_hub_handle"];
    const packet = {
      collection: "funding", release_id: "a".repeat(64), sample_rows: 1, source_rows: 12,
      display_order: names,
      codebook: { row_grain: "One award", aggregation_cautions: [], fields: names.map((name) => ({
        name, label: name, definition: "Fixture definition", display_disposition: "keep",
      })) },
      rows: [{ release_row_sha256: "b".repeat(64), row: {
        canonical_name: "Example organization", award_id: "AWARD-1",
        cicd_id: "retired-number", owner_hub_handle: "retired-handle",
      }, source: null }],
      limits: [],
    };
    const html = renderToStaticMarkup(jsx(ResearchPreview, { packet }));
    assert.ok(html.includes("1 real examples from"));
    assert.ok(html.includes("12"));
    assert.ok(html.includes("Example organization"));
    assert.ok(html.includes("AWARD-1"));
    for (const value of ["cicd_id", "owner_hub_handle", "retired-number", "retired-handle"]) {
      assert.equal(html.includes(value), false, value);
    }
  } finally { await vite.close(); }
});
