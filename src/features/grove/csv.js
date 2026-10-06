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
 * A cell a spreadsheet would run as a formula, made text. Most readers open a
 * download in Excel or Sheets, which execute a cell beginning with =, +, - or
 * @ (and, in some versions, one beginning with a tab or carriage return, or
 * with whitespace before one of those). Such a cell gets a leading
 * apostrophe, the way OWASP describes. A negative number is the one
 * exemption: "-4163330" must stay a number while "-1+HYPERLINK(...)", which
 * starts like one, must not (Codex, PR #63). Programmatic readers see the
 * apostrophe only on those cells, and the README says so.
 *
 * The API applies the same rule (server/cedar_press/csv_safety.py) and both
 * suites read one table of cases, server/tests/fixtures/csv_formula_cases.json.
 */
const NUMBER = /^-?\s*(\d[\d,]*)?(\.\d+)?$/;

export function spreadsheetSafe(value) {
  const text = String(value ?? "");
  const formula = /^[\t\r]/.test(text) || /^[ \t\r\n]*[=+@]/.test(text)
    || (/^[ \t\r\n]*-/.test(text) && !NUMBER.test(text.replace(/^[ \t\r\n]+|[ \t\r\n]+$/g, "")));
  return formula ? `'${text}` : text;
}

/** One CSV cell: spreadsheet-safe, and quoted when the value needs it. */
export function csvCell(value) {
  const text = spreadsheetSafe(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}
