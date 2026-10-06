import { PRESENTATION_COLUMNS } from "./mixedSpreadsheet.js";
/**
 * PURPOSE
 * How a record table is laid out: the money format, a collection's short
 * name, and which columns a table opens on.
 *
 * These sit beside the table component rather than inside it because both
 * the product's viewer and the signed-out door render that component, and a
 * module that exports a component plus three helpers cannot hot-reload.
 */

import { SOURCE_LINK_COLUMN, codebookColumns } from "./explore.js";
import { isInternalProvenanceColumn } from "./readerValues.js";
import { displayColumns } from "./showcase.js";
import { PRESS_CATALOG_BY_ID } from "./pressCatalog.js";
import { isRetiredIdentifierColumn } from "./readerPresentation.js";

export const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export function short(id) {
  return PRESS_CATALOG_BY_ID[id]?.short ?? id;
}

/**
 * The columns a table opens on, and the full set behind "show all".
 *
 * Extracted with the table itself: the door was showing Entity / Date /
 * Record / Amount while the product showed the collection's own fields in
 * the owner's reviewed order, which is the difference this returns.
 *
 * `lead` is the Cedar identity block in the register's order, pinned left.
 * `defaults` puts the contract's ROLES first — who the row is about, what it
 * says, how much, when, and where it came from — then whatever the release
 * declared. Review, 2026-09-15: "for this collection, prioritize entity,
 * program, amount, date, and source. Make other columns selectable."
 */
export function columnPlan(tableKey, contract, tableColumns, rows = []) {
  const publicColumns = tableColumns.filter((column) => !isRetiredIdentifierColumn(column));
  const has = (c) => c && publicColumns.includes(c);
  // A table whose link is BUILT from its identifiers (a USAspending award
  // key, a bill's congress and number, a Federal Register document number)
  // has no source column to show, so the table view showed no source at all
  // while the record page, reading `item.source`, did. The plan names a
  // column for it, and the table fills it from the same `rowSource`.
  const built = Boolean(contract?.source_builder || contract?.row_type_contracts) && !has(contract?.source);
  const source = built ? SOURCE_LINK_COLUMN : contract?.source;
  const shown = (c) => c === SOURCE_LINK_COLUMN ? built : has(c);
  const lead = contract ? [contract.entity_uid, contract.entity_name, contract.entity_type].filter(has) : [];
  const roleFirst = contract
    ? [contract.entity_name, ...(contract.observation ?? []), contract.amount, contract.date, source].filter(shown)
    : [];
  const declared = (contract?.default_columns ?? []).filter((column) => has(column) || (contract?.mapping_kind === "producer_spreadsheet" && Object.hasOwn(PRESENTATION_COLUMNS, column)));
  // The codebook's order is a fallback for a table with no declared view;
  // it is not a reason to open on a column of Cedar's own file names.
  const listed = tableKey ? codebookColumns(tableKey, publicColumns).filter((c) => !isInternalProvenanceColumn(c)) : [];
  // Producer spreadsheets and customer tables already declare the complete opening view, including
  // role and amount qualifications. A union's sparse component source columns
  // share the same dispatched source link that the record page uses.
  const dispatchedSources = new Set(built
    ? Object.values(contract?.row_type_contracts ?? {})
      .flatMap((type) => [type.source, type.source_fallback]).filter(Boolean)
    : []);
  // A customer table's contract (derive-explore customerTableContract) also
  // declares its complete opening view, so it opens on exactly that.
  const reviewedView = ["producer_spreadsheet", "customer_table"].includes(contract?.mapping_kind);
  const defaults = reviewedView && declared.length
    ? [...new Set([...declared.filter((column) => !dispatchedSources.has(column)), ...(built ? [SOURCE_LINK_COLUMN] : [])])]
    : [...new Set([...roleFirst, ...(declared.length ? declared : listed)])];
  const all = [...new Set([...lead, ...publicColumns, ...declared.filter((column) => Object.hasOwn(PRESENTATION_COLUMNS, column)), ...(built ? [SOURCE_LINK_COLUMN] : [])])];
  // The showcase's opening view (showcase.js): display defaults where the
  // declared view opens on blank or misleading columns, and never a column
  // blank in every example record.
  const opened = displayColumns(tableKey?.split("/")[0] ?? null, defaults, rows, [...publicColumns, ...(built ? [SOURCE_LINK_COLUMN] : [])]);
  return { lead, defaults: opened, all };
}

/** Display a reported point or bounds; never substitute an aggregate for either. */
export function reportedAmountText(item) {
  if (item?.amount != null) return money.format(item.amount);
  const range = item?.amountRange;
  if (!range || (range.lower == null && range.upper == null)) return null;
  if (range.lower == null) return "Up to " + money.format(range.upper);
  if (range.upper == null) return "At least " + money.format(range.lower);
  return money.format(range.lower) + " to " + money.format(range.upper);
}
