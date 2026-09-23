// REVIEW OWNER: Havala
//
// The record page's model: addressing one record, and coming back to where
// you were.
//
// WHY THIS EXISTS
// A record used to open inside the table, as a row that unfolded underneath
// the row it belonged to. The review's verdict, 2026-09-14: "the expanded row
// is effectively an entire record page squeezed into a table, and the
// explanations give every field equal visual weight." It also could not be
// sent to anyone — there was no URL for a record — and closing it lost the
// reader's place, because the table had been scrolled to reach it.
//
// So a record is a page with an address, and this module is the three things
// that page needs and the viewer must agree with it about:
//
//   1. THE ADDRESS. `recordHref` builds it and nothing else may: the key, the
//      record's own id (or its position when its table declares none), and
//      the cut the reader was looking at, carried as `from` so the way back
//      is the exact query they left.
//   2. THE WAY BACK. `rememberReturn` writes the scroll position and the cut
//      to session storage as the reader leaves; `takeReturn` hands it back
//      ONCE, to the viewer, and clears it. One-shot on purpose: a reader who
//      comes to /data later, by any other route, gets the top of the page.
//   3. THE NEIGHBOURS. Previous and next are the reader's own ordering — the
//      filtered, sorted list the table was showing — not the file's order, so
//      "next" means what the table said was next.
//
// Nothing here formats or invents a value. The inflation pair below is the
// one derivation, and it reads the file's own columns: a `<amount>_real<year>`
// column beside the amount, with the price year from `inflation_base_year`
// when the table carries one and from the column's own suffix otherwise. A
// table without those columns simply has no adjusted figure, and the page
// shows none rather than computing one.

import { PRESS_DATA_PATH, PRESS_RECORD_PATH } from "./pressRoutes.js";

/** Where the viewer's scroll and cut wait while the reader is on a record. */
const RETURN_KEY = "cp.record.return";

function sessionStore() {
  // Reading window.sessionStorage itself throws under a storage-denying
  // policy (sandboxed iframe, blocked site data), so this has to survive to
  // hand its callers null.
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

/**
 * A record's address.
 *
 * `from` is the viewer's query string as it stood — the cut, the sort and the
 * page — so "Back to results" is a link to the results, not to a fresh one.
 * A record whose table declares no id is addressed by its position in that
 * table's sample, which is stable for a given release and says so on the page.
 */
export function recordHref({ key, recordId = null, index = null, from = "" } = {}) {
  if (!key) return PRESS_DATA_PATH;
  const params = new URLSearchParams();
  params.set("k", key);
  if (recordId) params.set("r", recordId);
  else if (Number.isInteger(index)) params.set("i", String(index));
  if (from) params.set("from", from);
  return `${PRESS_RECORD_PATH}?${params.toString()}`;
}

/** What the record page was asked for. */
export function readRecordParams(search) {
  const params = new URLSearchParams(String(search ?? "").replace(/^\?/, ""));
  const index = Number.parseInt(params.get("i") ?? "", 10);
  return {
    key: params.get("k") ?? null,
    recordId: params.get("r") ?? null,
    index: Number.isFinite(index) && index >= 0 ? index : null,
    from: params.get("from") ?? "",
  };
}

/** The results the reader came from, as a link target. */
export function resultsHref(from) {
  return from ? `${PRESS_DATA_PATH}?${from}` : PRESS_DATA_PATH;
}

/**
 * Leaving the viewer for a record: keep the place. Called as the link is
 * followed, so the position written is the one the reader is looking at.
 */
export function rememberReturn({ search, y } = {}) {
  const store = sessionStore();
  if (!store) return;
  try {
    store.setItem(RETURN_KEY, JSON.stringify({ search: search ?? "", y: Math.max(0, Math.round(y ?? 0)) }));
  } catch {
    // Storage refused (private mode, quota). The cut is still in the URL;
    // only the scroll position is lost, which is the recoverable half.
  }
}

/**
 * The viewer asking whether it is a return, once.
 *
 * Returns null unless the stored entry is for the query being rendered — a
 * reader who edited the filters on the way back is not returning to the same
 * results, and scrolling them to where a different cut used to sit is worse
 * than the top of the page. Cleared whether or not it matched: this answers
 * the arrival it was written for and no later one.
 */
export function takeReturn(search) {
  const store = sessionStore();
  if (!store) return null;
  let raw;
  try {
    raw = store.getItem(RETURN_KEY);
    store.removeItem(RETURN_KEY);
  } catch {
    return null;
  }
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    const here = String(search ?? "").replace(/^\?/, "");
    if (String(parsed.search ?? "").replace(/^\?/, "") !== here) return null;
    return Number.isFinite(parsed.y) ? { y: parsed.y } : null;
  } catch {
    return null;
  }
}

/** Where a record sits in the reader's own ordering, and what is either side. */
export function neighbours(items, id) {
  const at = items.findIndex((item) => item.id === id);
  if (at < 0) return { at: -1, of: items.length, previous: null, next: null };
  return {
    at,
    of: items.length,
    previous: at > 0 ? items[at - 1] : null,
    next: at < items.length - 1 ? items[at + 1] : null,
  };
}

/**
 * The record asked for, from the rows of its table: by its own id, and by
 * position only when the table declares no id column. An id that is not in
 * this release's sample returns null, and the page says so rather than
 * showing a neighbouring record as though it were the one linked to.
 */
export function findRecord(items, { recordId = null, index = null } = {}) {
  if (recordId) return items.find((item) => item.recordId === recordId) ?? null;
  if (Number.isInteger(index)) return items[index] ?? null;
  return null;
}

const REAL = /^(.+)_real(\d{4})$/;

/**
 * The same money in a later year's dollars, where the file carries it.
 *
 * Read, never computed: `obligated_usd_real2025` beside `obligated_usd` is
 * the table's own adjusted figure, and `inflation_base_year` is the table's
 * own statement of which year's dollars those are. Where the two disagree the
 * column wins on the amount and the row wins on the year, because the row is
 * what the deflator was applied with. No such column, no second figure.
 */
export function realDollars(row, amountColumn) {
  if (!row || !amountColumn) return null;
  const direct = Object.keys(row).find((column) => {
    const match = REAL.exec(column);
    return match && match[1] === amountColumn;
  });
  if (!direct) return null;
  const text = String(row[direct] ?? "").trim();
  if (!text) return null;
  const value = Number(text.replace(/[$,\s]/g, ""));
  if (!Number.isFinite(value)) return null;
  const stated = String(row.inflation_base_year ?? "").trim();
  const year = /^\d{4}$/.test(stated) ? stated : REAL.exec(direct)[2];
  return { column: direct, value, year };
}
