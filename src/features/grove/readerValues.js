// REVIEW OWNER: Havala
//
// What a reader sees in place of Cedar's own plumbing.
//
// THE SOURCES VIEW LINKS TO THE EVIDENCE, NOT TO CEDAR'S WORKING FILES.
//
// The published samples carry two kinds of provenance side by side: the
// originating record a reader can open (a USAspending award, an LDA filing,
// a Federal Register notice) and the intermediate files and scripts Cedar
// built the row through (`ferc_ex_parte_parties.csv`, `code/1140`,
// `data/clean/federal_actions.csv`). The second kind is real lineage and the
// download keeps every byte of it. It is not something a reader can open,
// though, and printed as a raw path it reads as a link to somewhere that
// does not exist. So the viewer says what it is, "Cedar working file" or
// "Cedar pipeline script", and keeps the originating link the only thing that
// looks like one.
//
// The helpers are pure, so the node suite holds them without a browser:
//
//   firstUrl(text)      the first well-formed http(s) URL in a cell, or null.
//                       A cell like "https://a | https://b" or
//                       "https://portal.example/  (AS 45.55.139 filing)" is a
//                       real source followed by commentary; the whole cell
//                       is not an address, and used as an href it 404s.
//   linkText(url)       a link's visible text, cut to 80 characters with an
//                       ellipsis when it is longer.
//   readerText(text)    the cell with internal paths and file names named
//                       for what they are.
//   isInternalProvenanceColumn(column)
//                       whether a column holds that lineage, so no table or
//                       record opens on it.
//   tableLabel(table)   a release table's name for a reader: the manifest's
//                       own title where it has one, else the file stem made
//                       into words.
//
// No lookbehind anywhere below: a regular expression the browser cannot
// parse fails the whole module at load, not the one cell it was meant for.

/** A token that is an http(s) address with a host, and nothing after it. */
const URL_TOKEN = /^https?:\/\/[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?::\d+)?(?:[/?#][^\s|]*)?$/i;

/** Whether the whole value is one well-formed address. */
export function isWellFormedUrl(text) {
  return URL_TOKEN.test(String(text ?? "").trim());
}

/** The longest link text a record table shows, ellipsis included. */
export const LINK_TEXT_MAX = 80;

/**
 * A link's visible text: the address without its scheme or "www.", cut to
 * LINK_TEXT_MAX characters with an ellipsis. The cut and the ellipsis are
 * decided on the text shown, so a shortened link always says it was shortened.
 */
export function linkText(url, max = LINK_TEXT_MAX) {
  const shown = String(url ?? "").replace(/^https?:\/\/(www\.)?/i, "");
  return shown.length > max ? `${shown.slice(0, max - 1)}…` : shown;
}

/** A scheme with nothing behind it ("https://"): a blank in the source, not a link. */
export function isBareScheme(text) {
  return /^https?:\/\/\s*$/i.test(String(text ?? ""));
}

/**
 * The first well-formed address in a cell, or null.
 *
 * Tokens are split on whitespace and the collections' own `|` list
 * separator; trailing punctuation a sentence put there is not part of the
 * address. Nothing is repaired: a token that is not an address is skipped,
 * never guessed into one.
 */
export function firstUrl(text) {
  const tokens = String(text ?? "").split(/[\s|]+/);
  for (const raw of tokens) {
    const token = raw.replace(/[),.;:]+$/, "");
    if (URL_TOKEN.test(token)) return token;
  }
  return null;
}

// ── Internal files ─────────────────────────────────────────────────────────

// What may stand immediately before an internal reference. A `/` is not in
// the set, which is what keeps the file name at the end of a URL a URL.
const LEAD = String.raw`(^|[\s(|;,+:="'\[])`;

// A path under the workspace's own roots, or a machine's home directory. A
// `code/` path counts only when it looks like a script (a number or a
// snake_case name), so "zip code/city" stays prose.
const PATH = String.raw`(?:~|\/Users|\/home|data|dist|docs|code(?=\/(?:\d|\w+_)))\/[^\s|;,()"'<>\[\]]*[^\s|;,()"'<>\[\].:]`;

// A bare file name with an extension Cedar's pipeline writes or runs, plus a
// `:column` or `::function` suffix where the value names one.
const FILE = String.raw`[\w.-]*\w\.(?:csv|py|jsonl|parquet|dta|do)(?:::?\w+)?`;

const TAIL = String.raw`(?=$|[\s)|;,+"'.:\]])`;

const INTERNAL = new RegExp(`${LEAD}(${PATH}|${FILE})${TAIL}`, "gi");

const PREPOSITION = /\b(?:in|from|by|to|on|of|at|via|into|through|against|under|with|using)\s+$/i;

const WORKING_FILE = "Cedar working file";
const PIPELINE_SCRIPT = "Cedar pipeline script";

function labelFor(token) {
  return /^code\//i.test(token) || /\.py(?:::?\w+)?$/i.test(token) ? PIPELINE_SCRIPT : WORKING_FILE;
}

/** Whether a cell names one of Cedar's own files, scripts or a machine path. */
export function namesInternalFile(text) {
  INTERNAL.lastIndex = 0;
  const hit = INTERNAL.test(String(text ?? ""));
  INTERNAL.lastIndex = 0;
  return hit;
}

/**
 * The cell as a reader should see it: every internal reference named for
 * what it is. A cell that is nothing but references (a list of files, a
 * script and its output) becomes the one phrase; a sentence keeps its
 * words and says "a Cedar working file" where it named a path.
 */
export function readerText(text) {
  const value = String(text ?? "");
  const found = [];
  let out = "";
  let last = 0;
  INTERNAL.lastIndex = 0;
  let match;
  while ((match = INTERNAL.exec(value)) !== null) {
    const [whole, lead, token] = match;
    const start = match.index + lead.length;
    const before = value.slice(0, start);
    const label = labelFor(token);
    found.push(label);
    out += value.slice(last, start) + (PREPOSITION.test(before) ? `a ${label}` : label);
    last = match.index + whole.length;
    // A zero-width lead at the start of the string cannot loop: the token
    // is never empty, so the index always moves.
  }
  INTERNAL.lastIndex = 0;
  if (!found.length) return value;
  out += value.slice(last);
  // Nothing but references, separators and the words "a"? Then one phrase.
  const residue = out
    .replace(new RegExp(`\\b(?:a )?(?:${WORKING_FILE}|${PIPELINE_SCRIPT})\\b`, "g"), "")
    .replace(/[\s|;,+>=:-]+/g, "");
  if (!residue) {
    if (found.length === 1) return found[0];
    return found.every((label) => label === PIPELINE_SCRIPT) ? "Cedar pipeline scripts" : "Cedar working files";
  }
  return out;
}

// Columns whose values are Cedar's own lineage: the file a row came through,
// the script that parsed it, the ledger it was checked against, or the prose
// basis for a step. Real, kept in every download, shown in the record's
// additional details; never what a table or a record opens on.
const INTERNAL_COLUMNS = new Set([
  "source_dataset", "source_files", "source_file", "source_or_forum", "source_inbox",
  "parent_dataset", "local_file", "already_parsed_by", "compared_against",
  "link_ledger_source_file", "measured_from", "bill_title_source", "classifier",
]);

/** Whether a column is one of Cedar's lineage columns rather than a fact about the record. */
export function isInternalProvenanceColumn(column) {
  const name = String(column ?? "").toLowerCase();
  return INTERNAL_COLUMNS.has(name) || /_basis$/.test(name);
}

// ── Table names ────────────────────────────────────────────────────────────

// Initialisms the table stems carry, kept in capitals so "fr_nagpra_title_index"
// reads as "FR NAGPRA title index" and not "Fr nagpra title index".
const ACRONYMS = new Map(
  [
    "ANC", "ANCSA", "BIA", "BIE", "CAGE", "EDGAR", "EIN", "FAADS", "FAC", "FERC", "FOIA", "FPDS",
    "FR", "HCP", "LDA", "NAGPRA", "NEED", "NEPA", "NP", "NPS", "NRC", "OIRA", "RHC", "SAM", "SEC",
    "SEFA", "UEI", "UIO", "USAC",
  ].map((word) => [word.toLowerCase(), word]),
);

function wordFor(word, first) {
  const lower = word.toLowerCase();
  if (ACRONYMS.has(lower)) return ACRONYMS.get(lower);
  if (/^ueis$/i.test(word)) return "UEIs";
  if (/^fy\d{4}$/i.test(word)) return word.toUpperCase();
  return first ? lower.charAt(0).toUpperCase() + lower.slice(1) : lower;
}

/**
 * A release table's name for a reader. The manifest's own `title` or
 * `label` wins where it carries one; otherwise the file stem, without
 * `.csv`, underscores as spaces, in sentence case.
 */
export function tableLabel(table) {
  const declared = table?.title ?? table?.label;
  if (declared) return String(declared);
  const stem = String(table?.table ?? table?.key ?? "").split("/").pop().replace(/\.csv$/i, "");
  const words = stem.split("_").filter(Boolean);
  return words.map((word, i) => wordFor(word, i === 0)).join(" ");
}
