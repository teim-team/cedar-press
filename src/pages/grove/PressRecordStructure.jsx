// REVIEW OWNER: Havala
//
// What each record holds, in the same frame a collection's sample records
// fill: the field and what it means, one row each. For the collections
// Cedar Press presents by their record structure (Foundation & Corporate
// Giving, PLOT; `pressRecordStructure.js` holds the fields and their
// sources). It is drawn with the product's own table, because on a Cedar
// Press page the strongest object is a record table, and a field list is the
// honest table for a collection with no sample rows here. No row count, year
// span or sample value appears in it.

import { RECORD_STRUCTURE_TITLE, recordStructure } from "../../features/grove/pressRecordStructure.js";

/** The caption line above the list: the title, and how many fields. */
export function RecordStructureCap({ collectionId, className = "cp-pane__tablecap" }) {
  const structure = recordStructure(collectionId);
  if (!structure) return null;
  return (
    <p className={className}>
      <span>{RECORD_STRUCTURE_TITLE}</span>
      <span>{structure.fields.length} fields</span>
    </p>
  );
}

/** The field list as a table, or nothing for a collection that shows sample records. */
export function RecordStructureTable({ collectionId, name }) {
  const structure = recordStructure(collectionId);
  if (!structure) return null;
  return (
    <div className="cp-ex__scrollwrap cp-struct" data-testid="record-structure" data-collection={collectionId}>
      <div className="cp-ex__scroll">
        <table className="cp-ex__table cp-ex__table--table cp-struct__table">
          <caption className="cp-badge__sr">
            {RECORD_STRUCTURE_TITLE}{name ? ` in ${name}` : ""}
          </caption>
          <thead>
            <tr>
              <th scope="col" className="cp-ex__c-text">Field</th>
              <th scope="col" className="cp-ex__c-text">What it holds</th>
            </tr>
          </thead>
          <tbody>
            {structure.fields.map((field) => (
              <tr key={field.name}>
                <th scope="row" className="cp-struct__name">
                  {structure.kind === "columns" ? <code>{field.name}</code> : field.name}
                </th>
                <td className="cp-struct__meaning">{field.meaning}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
