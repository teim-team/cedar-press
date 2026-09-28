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
