// REVIEW OWNER: Havala
//
// What a Cedar Press download hands over, and the handing over.
//
// A tile IS the download: click it and the file arrives, with no detail page
// in between. That decision retired the per-collection pages; the What's New
// feed is the one place that tracks changes, because one tracker is
// something a reader checks and eleven is something they don't.
//
// Eleven of the twelve collections ship a real preview extract: ten rows of
// the collection's flagship table, straight out of Cedar's review bundle
// (code/1135_full_dataset_review_bundle.py). The twelfth, and any shelf entry
// with no release behind it, hands over what Cedar holds about the collection
// itself: coverage, shelf, contents and what it is joined to. Every download
// is something true; none of it is invented rows.
//
// THE PREVIEW IS NOT THE RELEASE
// Ten rows is a sample and the surface must never call it the dataset. The
// full spreadsheets are 6.2 GB and single tables exceed GitHub's file limit,
// so they are not in this repository at all: `collectionTables()` carries
// every table's row count, split and file count so a serving layer can find
// the real file, and the manifest's `full_files.served` is `false` until one
// exists.
//
// WHY THESE ARE ASYNC
// The sample rows are static files the built site serves, not bundled bytes:
// 169 sample files across the twelve collections is 1.4 MB of CSV, and
// inlining it would load every reader's page for a button most never press.
// So the file is fetched at click time. `hasSample` answers from the manifest
// alone, with no fetch, because a tile has to label itself before the click.

import { collectionCitation, collectionCsv, hasSample, samplePath } from "./collection.js";
import { coverageLabel } from "./pressAccess.js";

const csvCell = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;

/**
 * Whether a real extract exists for this collection. Everything else
 * downloads a description of the collection, and the surface has to say so:
 * a tile labeled "Download Federal Register" that hands over two columns of
 * metadata is a broken promise to a paying reader.
 *
 * Answered from the manifest, synchronously: this decides a label, and a
 * label that has to await a network round trip renders wrong first.
 */
export function hasReleaseFile(entry) {
  return hasSample(entry?.id);
}

/**
 * The file for a collection: the shipped extract, or its own description.
 *
 * `fetchText` is injectable so this can be exercised without a network and
 * without a DOM; it defaults to fetching the sample the manifest names.
 */
export async function csvFor(entry, fetchText = defaultFetchText) {
  if (hasSample(entry.id)) {
    const text = await fetchText(samplePath(entry.id));
    const shipped = text == null ? null : collectionCsv(entry.id, text);
    if (shipped) return { csv: shipped, name: `${entry.id}.csv` };
  }
  // The file outlives the page, so it carries its own citation. Launch
  // datasets cite with their version; the rest of the shelf has no release
  // bookkeeping yet and cites by name.
  const citation =
    collectionCitation(entry.id) ||
    `Lumecon, "${entry.name}", Cedar Press collection, cedarpress.ai.`;
  const rows = [
    ["field", "value"],
    ["collection", entry.name],
    ["shelf", entry.shelf || entry.kind || ""],
    // The label, not the year: a roster has no year, and an empty
    // coverage cell in a file that outlives the page reads as unknown
    // rather than as "this is a roster".
    ["coverage", coverageLabel(entry)],
    ["contents", entry.blurb || ""],
    ["entity_linkage", entry.linkage || ""],
    ["cite_as", citation],
  ];
  return {
    csv: rows.map((row) => row.map(csvCell).join(",")).join("\n"),
    name: `${entry.id}-collection-description.csv`,
  };
}

/**
 * Fetch a sample file's text, or `null` if it cannot be read.
 *
 * A failed fetch falls back to the collection description rather than
 * throwing: a download button that does nothing is worse than one that hands
 * over the honest smaller thing, and the filename says which one arrived.
 */
async function defaultFetchText(path) {
  try {
    const response = await fetch(path);
    return response.ok ? await response.text() : null;
  } catch {
    return null;
  }
}

export async function downloadCsv(entry) {
  const { csv, name } = await csvFor(entry);
  if (!csv) return;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

// CRC-32, needed by the ZIP directory. Table-driven, computed once.
const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/**
 * A stored (uncompressed) ZIP of text files. Hand-rolled because the shelf
 * needs exactly one browser download per gesture and nothing more: firing one
 * download per collection left every click after the first outside the user's
 * transient activation, which download blockers then swallow.
 */
function zipOf(files) {
  const encoder = new TextEncoder();
  const parts = [];
  const central = [];
  let offset = 0;
  for (const file of files) {
    const nameBytes = encoder.encode(file.name);
    const data = encoder.encode(file.text);
    const crc = crc32(data);
    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true);
    local.setUint16(4, 20, true);
    local.setUint16(6, 0x0800, true); // UTF-8 names
    local.setUint16(8, 0, true); // stored, no compression
    local.setUint32(14, crc, true);
    local.setUint32(18, data.length, true);
    local.setUint32(22, data.length, true);
    local.setUint16(26, nameBytes.length, true);
    parts.push(local.buffer, nameBytes, data);
    const dir = new DataView(new ArrayBuffer(46));
    dir.setUint32(0, 0x02014b50, true);
    dir.setUint16(4, 20, true);
    dir.setUint16(6, 20, true);
    dir.setUint16(8, 0x0800, true);
    dir.setUint16(10, 0, true);
    dir.setUint32(16, crc, true);
    dir.setUint32(20, data.length, true);
    dir.setUint32(24, data.length, true);
    dir.setUint16(28, nameBytes.length, true);
    dir.setUint32(42, offset, true);
    central.push(dir.buffer, nameBytes);
    offset += 30 + nameBytes.length + data.length;
  }
  const centralSize = central.reduce((size, part) => size + part.byteLength, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true);
  end.setUint16(8, files.length, true);
  end.setUint16(10, files.length, true);
  end.setUint32(12, centralSize, true);
  end.setUint32(16, offset, true);
  return new Blob([...parts, ...central, end.buffer], { type: "application/zip" });
}

/**
 * Everything on a shelf, one click, ONE download: an archive. Spacing
 * separate downloads out does not preserve the user's transient activation,
 * so browsers that block automatic downloads delivered only the first file.
 *
 * The await before the anchor is new and is a known risk to that same
 * transient activation: the samples are fetched rather than bundled, so the
 * click that started this may have aged out by the time the archive exists.
 * The fetches are parallel and the files are small (1.4 MB across all twelve),
 * which keeps the window short, and one archive is still strictly better than
 * a dozen downloads. If a blocker is seen swallowing it, the fix is to
 * prefetch on hover, not to inline 1.4 MB of CSV into the page.
 */
export async function downloadAll(entries, archiveName = "cedar-press-samples.zip") {
  // Fetched together rather than one after another: a shelf is a dozen
  // collections and a serial await per tile is a dozen round trips before
  // the first byte of the archive exists.
  const built = await Promise.all(entries.map((entry) => csvFor(entry)));
  const files = built
    .filter((file) => file.csv)
    .map((file) => ({ name: file.name, text: file.csv }));
  if (!files.length) return;
  const blob = zipOf(files);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = archiveName;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
