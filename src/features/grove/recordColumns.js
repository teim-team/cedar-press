/**
 * PURPOSE
 * How a record table is laid out: the money format, a collection's short
 * name, and which columns a table opens on.
 *
 * These sit beside the table component rather than inside it because both
 * the product's viewer and the signed-out door render that component, and a
 * module that exports a component plus three helpers cannot hot-reload.
 */

import { codebookColumns } from "./explore.js";
import { PRESS_CATALOG_BY_ID } from "./pressCatalog.js";

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
export function columnPlan(tableKey, contract, tableColumns) {
  const has = (c) => c && tableColumns.includes(c);
  const lead = contract ? [contract.entity_uid, contract.entity_name, contract.entity_type].filter(has) : [];
  const roleFirst = contract
    ? [contract.entity_name, ...(contract.observation ?? []), contract.amount, contract.date, contract.source].filter(has)
    : [];
  const declared = (contract?.default_columns ?? []).filter(has);
  const listed = tableKey ? codebookColumns(tableKey, tableColumns) : [];
  const defaults = [...new Set([...roleFirst, ...(declared.length ? declared : listed)])];
  const all = [...new Set([...lead, ...tableColumns])];
  return { lead, defaults, all };
}
