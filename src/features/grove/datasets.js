/**
 * PURPOSE
 * Datasets a subscriber brings to the service.
 *
 * Connected, an upload goes to the platform: the file is the payload, the
 * database holds it, and every reader on the subscription sees it. This
 * module is then a thin pass-through to the API and holds no data of its
 * own.
 *
 * Standalone, there is nowhere to put a file, so the upload is parsed in the
 * browser and kept in this browser's storage — enough to exercise the flow
 * end to end (choose a file, see it shelved, take it back) while the cards
 * say plainly that nothing was published. The two paths return the same
 * descriptor shape, so the interface above them does not branch.
 */
import * as api from "../../api.js";
import { isConnected } from "../../config.js";

const LOCAL_KEY = "cedar-press-datasets";
const MAX_LOCAL_ROWS = 500;
const MAX_FIGURE_POINTS = 12;

/* ── CSV ─────────────────────────────────────────────────────────────── */

/** One CSV line to fields, honoring double-quoted values. */
export function splitCsvLine(line) {
  const fields = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      fields.push(field);
      field = "";
    } else {
      field += ch;
    }
  }
  fields.push(field);
  return fields;
}

export function parseCsv(text) {
  const lines = String(text)
    .split(/\r\n|\r|\n/)
    .filter((line) => line.trim() !== "");
  if (lines.length < 2) {
    throw new Error("That file needs a header row and at least one data row.");
  }
  return {
    header: splitCsvLine(lines[0]).map((cell) => cell.trim()),
    rows: lines.slice(1).map((line) => splitCsvLine(line)),
  };
}

/** Label plus number in the first two columns draws the same mark the shelf uses. */
export function figurePointsFrom(rows) {
  if (!rows.length || !rows.every((row) => row.length >= 2)) return null;
  const points = rows.slice(0, MAX_FIGURE_POINTS).map((row) => ({
    label: String(row[0]).trim(),
    value: Number(String(row[1]).trim().replace(/[$,%\s]/g, "")),
  }));
  const usable = points.every(
    (point) => point.label !== "" && Number.isFinite(point.value) && point.value >= 0,
  );
  return usable && points.some((point) => point.value > 0) ? points : null;
}

export function toCsv(header, rows) {
  return [header, ...rows]
    .map((row) =>
      row
        .map((cell) => {
          const value = String(cell ?? "");
          return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
        })
        .join(","),
    )
    .join("\n");
}

/** A file name to a readable dataset name. */
function nameFrom(fileName) {
  const base = fileName.replace(/\.csv$/i, "").replace(/[-_]+/g, " ").trim();
  if (!base) return "Uploaded dataset";
  return base.charAt(0).toUpperCase() + base.slice(1);
}

/* ── Local shelf (standalone) ────────────────────────────────────────── */

function readLocal() {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function writeLocal(list) {
  try {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(list));
    return true;
  } catch {
    return false;
  }
}

/* ── The two paths, one shape ────────────────────────────────────────── */

/**
 * A dataset descriptor:
 * { id, name, fileName, rowCount, columns, points, uploadedAt, published }
 * `published` is the honest bit: true only when the platform holds it.
 */
export async function listDatasets({ signal } = {}) {
  if (isConnected()) {
    const payload = await api.fetchDatasets({ signal });
    return (payload?.datasets ?? payload ?? []).map((entry) => ({ ...entry, published: true }));
  }
  return readLocal();
}

export async function addDataset({ file, text, now = new Date() }) {
  if (isConnected()) {
    const saved = await api.uploadDataset({ file, name: nameFrom(file.name) });
    return { ...saved, published: true };
  }
  const { header, rows } = parseCsv(text);
  const kept = rows.slice(0, MAX_LOCAL_ROWS);
  const dataset = {
    id: `local-${now.getTime()}`,
    name: nameFrom(file.name),
    fileName: file.name,
    header,
    rows: kept,
    rowCount: rows.length,
    columns: header.length,
    truncated: rows.length > kept.length,
    points: figurePointsFrom(rows),
    uploadedAt: now.toISOString(),
    published: false,
  };
  if (!writeLocal([dataset, ...readLocal()])) {
    throw new Error("This browser is not letting the preview store the file.");
  }
  return dataset;
}

export async function removeDataset(id) {
  if (isConnected()) {
    await api.deleteDataset(id);
    return;
  }
  writeLocal(readLocal().filter((dataset) => dataset.id !== id));
}

/** The rows back out. Connected, the platform serves the file it holds. */
export async function datasetCsv(dataset) {
  if (dataset.published) {
    const { blob } = await api.downloadCollection(dataset.id);
    return blob;
  }
  return new Blob([toCsv(dataset.header, dataset.rows)], { type: "text/csv;charset=utf-8" });
}
