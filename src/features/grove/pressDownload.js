// REVIEW OWNER: Havala
//
// What a Cedar Press download hands over, and the handing over.
//
// A tile IS the download: click it and the file arrives, with no detail page
// in between. That decision retired the per-collection pages; the What's New
// feed is the one place that tracks changes, because one tracker is
// something a reader checks and eleven is something they don't.
//
// Three collections ship with a real figure extract. The rest hand over what
// Cedar holds about the collection itself: coverage, shelf, contents and
// what it is joined to. Every download is something true; none of it is
// invented rows. Real release bundles replace these when the data layer's
// serializers exist (see docs/cedar-grove-press-boundary.md).

import { collectionCitation, collectionCsv } from "./collection.js";

const csvCell = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;

/**
 * Whether a real release extract exists for this collection. Everything else
 * downloads a description of the collection, and the surface has to say so:
 * a tile labeled "Download Federal Register" that hands over two columns of
 * metadata is a broken promise to a paying reader.
 */
export function hasReleaseFile(entry) {
  return Boolean(collectionCsv(entry?.id));
}

/** The file for a collection: the shipped extract, or its own description. */
export function csvFor(entry) {
  const shipped = collectionCsv(entry.id);
  if (shipped) return { csv: shipped, name: `${entry.id}.csv` };
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
    ["coverage_from", entry.historyFrom || ""],
    ["contents", entry.blurb || ""],
    ["entity_linkage", entry.linkage || ""],
    ["cite_as", citation],
  ];
  return {
    csv: rows.map((row) => row.map(csvCell).join(",")).join("\n"),
    name: `${entry.id}-collection-description.csv`,
  };
}

export function downloadCsv(entry) {
  const { csv, name } = csvFor(entry);
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
 */
export function downloadAll(entries, archiveName = "cedar-press-collections.zip") {
  const files = entries
    .map((entry) => csvFor(entry))
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
