/**
 * PURPOSE
 * Subscriber-uploaded datasets, the mockup's version.
 *
 * The real feature sends the file to the backend, which validates, versions
 * and shelves it. Until that server work lands, an upload is parsed in the
 * browser and kept in localStorage, clearly labeled as a local preview: it
 * demonstrates the flow (choose a CSV, see it on the shelf, download it back)
 * without pretending anything was published.
 *
 * Parsing is deliberately simple: header row plus data rows, comma-separated
 * with quoted fields honored. If the first two columns read as label + number,
 * the shelf can draw the same bar mark the launch collection uses; otherwise
 * the card shows the dataset's shape and skips the figure.
 */

const UPLOADS_KEY = "cedar-press-uploads";
const MAX_FIGURE_POINTS = 12;
const MAX_STORED_ROWS = 500;

export function storedUploads() {
  try {
    const raw = localStorage.getItem(UPLOADS_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function persist(uploads) {
  try {
    localStorage.setItem(UPLOADS_KEY, JSON.stringify(uploads));
    return true;
  } catch {
    return false;
  }
}

/** One CSV line -> fields, honoring double-quoted values. */
function splitCsvLine(line) {
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
  const header = splitCsvLine(lines[0]).map((cell) => cell.trim());
  const rows = lines.slice(1).map((line) => splitCsvLine(line));
  return { header, rows };
}

/** label + numeric value in the first two columns -> figure points. */
function figurePointsFrom(rows) {
  if (!rows.every((row) => row.length >= 2)) return null;
  const points = rows.slice(0, MAX_FIGURE_POINTS).map((row) => ({
    label: String(row[0]).trim(),
    value: Number(String(row[1]).trim().replace(/[$,%\s]/g, "")),
  }));
  const usable = points.every(
    (point) => point.label !== "" && Number.isFinite(point.value) && point.value >= 0,
  );
  return usable && points.some((point) => point.value > 0) ? points : null;
}

/**
 * Shelve a parsed CSV. Returns the stored descriptor; throws when the file
 * doesn't parse. `now` arrives from the caller so this module stays pure.
 */
export function addUpload({ fileName, text, now }) {
  const { header, rows } = parseCsv(text);
  const kept = rows.slice(0, MAX_STORED_ROWS);
  const name = fileName.replace(/\.csv$/i, "").replace(/[-_]+/g, " ").trim() || "Uploaded dataset";
  const upload = {
    id: `upload-${now.getTime()}`,
    name: name.charAt(0).toUpperCase() + name.slice(1),
    fileName,
    header,
    rows: kept,
    rowCount: rows.length,
    truncated: rows.length > kept.length,
    points: figurePointsFrom(rows),
    uploadedAt: now.toISOString(),
  };
  const uploads = [upload, ...storedUploads()];
  if (!persist(uploads)) {
    throw new Error("This browser is not letting the preview store the file.");
  }
  return upload;
}

export function removeUpload(id) {
  persist(storedUploads().filter((upload) => upload.id !== id));
}

/** The rows back out, exactly as stored. */
export function uploadCsv(upload) {
  return [upload.header, ...upload.rows]
    .map((row) =>
      row
        .map((cell) => {
          const value = String(cell);
          return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
        })
        .join(","),
    )
    .join("\n");
}
