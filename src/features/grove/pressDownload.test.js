// What a Cedar Press download hands over: every file carries its own
// citation, because a saved file outlives the page it came from and
// provenance that lives only in the UI is provenance the reader loses.

import assert from "node:assert/strict";
import test from "node:test";

import { csvFor, hasReleaseFile } from "./pressDownload.js";

test("a launch dataset downloads its extract, citation row included", () => {
  const { csv, name } = csvFor({ id: "deals", name: "Indian Country Deals" });
  assert.equal(name, "deals.csv");
  const last = csv.split("\n").at(-1);
  assert.ok(last.startsWith('cite_as,"Lumecon, ""'), last);
  assert.ok(last.includes("v9"));
});

test("a shelf collection without release bookkeeping cites by name", () => {
  const entry = {
    id: "not-a-launch-dataset",
    name: "Example Shelf Collection",
    shelf: "standard",
    historyFrom: "2015",
    blurb: "What it holds.",
    linkage: "Joined to the entity layer.",
  };
  const { csv, name } = csvFor(entry);
  // The filename says what the file is: a description of the collection,
  // never the collection's rows. The surface reads hasReleaseFile to label
  // the tile the same way before the click.
  assert.equal(hasReleaseFile(entry), false);
  assert.equal(name, "not-a-launch-dataset-collection-description.csv");
  const lines = csv.split("\n");
  assert.equal(lines[0], '"field","value"');
  const citeLine = lines.at(-1);
  assert.ok(citeLine.startsWith('"cite_as"'), citeLine);
  assert.ok(citeLine.includes("Example Shelf Collection"));
  assert.ok(citeLine.includes("cedarpress.ai"));
});
