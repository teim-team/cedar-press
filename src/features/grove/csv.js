// Shared CSV parsing and spreadsheet-safe cells.
export function parseCsv(text) {
  const source = String(text ?? "").replace(/^\uFEFF/, "");
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < source.length; i += 1) {
    const ch = source[i];
    if (quoted) {
      if (ch === '"' && source[i + 1] === '"') { cell += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && source[i + 1] === "\n") i += 1;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else cell += ch;
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  const [columns = [], ...body] = rows;
  const records = body
    .filter((cells) => cells.length > 1 || (cells.length === 1 && cells[0] !== ""))
    .map((cells) => Object.fromEntries(columns.map((name, i) => [name, cells[i] ?? ""])));
  return { columns, rows: records };
}

/**
 * One CSV cell. Quoted when the value needs it. A cell that a spreadsheet
 * would read as a formula (leading =, +, @, or a - that does not start a
 * number) gets a leading apostrophe, the way OWASP describes: the file is
 * opened in Excel by most readers, and "-4163330" must stay a number while
 * "=HYPERLINK(...)" must stay text. Programmatic readers see the apostrophe
 * only on those cells, and the README says so.
 */
const NUMBER = /^-?\s*(\d[\d,]*)?(\.\d+)?$/;

export function csvCell(value) {
  let text = String(value ?? "");
  // A leading minus is exempt only when the WHOLE value is a number:
  // "-1+HYPERLINK(...)" starts like one and is not (Codex, PR #63).
  if (/^[=+@]/.test(text) || /^[\t\r]/.test(text) || (/^-/.test(text) && !NUMBER.test(text))) text = `'${text}`;
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

