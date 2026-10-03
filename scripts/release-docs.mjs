// Documentation contracts for installed producer spreadsheets.
// A dictionary is documentation, not evidence of publication permission.
export function releasedTableKey(entry) {
  if (!entry?.sample?.path?.endsWith("/spreadsheet__10.csv")) return null;
  const table = entry.sample.table;
  if (typeof table !== "string" || !/^[a-z0-9_-]+\.csv$/i.test(table)) {
    throw new Error("Installed spreadsheet has no unambiguous manifest table name");
  }
  return `${entry.id}/${table.slice(0, -4)}`;
}

export function assertReleasedDictionary(book, sample = null) {
  if (!book || !Array.isArray(book.fields) || !book.fields.length || !book.row || !book.where) {
    throw new Error("Installed spreadsheet requires its producer dictionary, row grain and release location");
  }
  const names = book.fields.map((field) => field.column);
  if (names.some((name) => typeof name !== "string" || !name) || new Set(names).size !== names.length) {
    throw new Error("Installed spreadsheet dictionary contains missing or duplicate columns");
  }
  for (const field of book.fields) {
    if (typeof field.label !== "string" || !field.label.trim() ||
        typeof field.meaning !== "string" || !field.meaning.trim() ||
        /^Reviewed Cedar field contract:\s*/i.test(field.meaning) ||
        /^See the exact release contract\.?$/i.test(field.meaning.trim()) ||
        [field.column, field.column.split("__").at(-1)].flatMap((name) => [name.toLowerCase(), name.replace(/_/g, " ").toLowerCase()]).includes(field.meaning.trim().toLowerCase())) {
      throw new Error(`Substantive definition required for ${field.column}`);
    }
    if (field.add || field.rename_to || field.combine_into) {
      throw new Error(`Installed spreadsheet dictionary must describe the exported column ${field.column} directly`);
    }
  }
  if (sample && (sample.columns.length !== names.length ||
      sample.columns.some((column, index) => column !== names[index]))) {
    throw new Error("Installed spreadsheet dictionary must match the served CSV header exactly");
  }
  return book;
}

export function releasedBook(entry, codebook, sample = null) {
  const key = releasedTableKey(entry);
  if (!key) return null;
  const book = codebook.tables[key];
  if (book?.collection !== entry.id) throw new Error(`Missing installed spreadsheet dictionary: ${key}`);
  return { key, book: assertReleasedDictionary(book, sample) };
}
