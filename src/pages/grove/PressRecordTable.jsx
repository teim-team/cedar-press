// REVIEW OWNER: Havala
//
// The record table, and the list it becomes on a phone.
//
// ONE TABLE, TWO PLACES.
//
// This used to live inside `PressExplore`, which meant the signed-out door
// could not use it and drew a table of its own: four columns of its own
// naming, its own classes, its own cell rules. A visitor therefore compared
// a marketing table against a product table and was told they were the same
// thing. The brief's Priority 0 is blunt about it — "the public sample
// loader may be a mode adapter, but it cannot be a separately designed
// table" — so the table moved out here and both surfaces render it.
//
// The door mounts it `readOnly`: no sort buttons, no open-the-record column,
// no row click, because none of those lead anywhere without a subscription.
// Everything else — the pinned Cedar identity block, the column order, the
// money and date and yes-or-no rules in `Human`, the edge fade — is the same
// code, so "visually the same table" is a fact about the source rather than
// a resemblance somebody has to keep up by hand.

import { useEffect, useRef } from "react";
import { Link } from "react-router";

import {
  WITHHELD_TEXT,
  labelFor,
  meaningFor,
  scopeName,
} from "../../features/grove/explore.js";
import { money, short } from "../../features/grove/recordColumns.js";
import { scrollEdges } from "../../features/grove/scrollEdges.js";

export function Human({ column, value, contract, item = null }) {
  if (value === "" || value == null) return "—";
  const text = String(value);
  if (/^https?:\/\/\S+$/i.test(text)) return <a href={text} target="_blank" rel="noreferrer">{text.replace(/^https?:\/\/(www\.)?/, "").slice(0, 80)}{text.length > 88 ? "…" : ""}</a>;
  // Money wherever the column is money: the table's amount, or any column
  // named in dollars (`_usd`, `_amt`, `obligations`, `amount`, `value_usd`).
  if (contract?.amount === column || /(_usd|_amt|obligations|_amount|amount_usd)$/i.test(column) || /^(income|expenses|spend)_/i.test(column)) {
    const n = Number(text.replace(/[$,\s]/g, ""));
    if (Number.isFinite(n)) return money.format(n);
  }
  if (/^\d{4}-\d{2}-\d{2}T/.test(text)) return text.slice(0, 10);
  // Yes or no wherever the codebook says the column is one, or the name does.
  const yesNo = /\(yes or no\)/.test(meaningFor(item?.key, column) ?? "") || /^(is_|has_|self_|reported_)|_flag$/.test(column);
  if (yesNo && /^(0|1|Y|N)$/i.test(text)) return /^(1|Y)$/i.test(text) ? "yes" : "no";
  if (text.includes("|") && !/^https?:/.test(text)) return text.split("|").map((p) => p.trim()).filter(Boolean).join(", ");
  // A JSON array cell (the approved schema's plural block and lists) reads
  // as a list, an unresolved member as "unresolved", an object by its url.
  if (/^\[/.test(text)) {
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        if (!parsed.length) return "—";
        return parsed.map((p) => (p == null ? "unresolved" : typeof p === "object" ? (p.url ?? JSON.stringify(p)) : String(p))).join(", ");
      }
    } catch {
      // Not JSON: shown as it is.
    }
  }
  return text;
}

/** A scope element in words: the population and the relationship. */
function scopeLine(el) {
  const rel = { addressed: "addressed to", applies_to: "applies to", eligible_class: "eligible class:", aggregate_population: "describes collectively", general_subject: "concerns" }[el.relationship] ?? el.relationship;
  return `${rel} ${scopeName(el.scope)}`;
}

export function EntityCell({ item }) {
  const { entities } = item.entity;
  const first = entities[0];
  const why = item.why ?? [];
  if (!first) {
    // What the blank says is the table's own link status where it carries
    // one; a scope alone does not make a blank "no individual named", since
    // a notice can address a population AND name a party the register could
    // not place (Codex, PR #69).
    const blank = { no_individual_named: "no individual entity named", unresolved: "named party not resolved to the register", withheld: "identity withheld" }[item.linkStatus]
      ?? "not linked to an entity";
    return (
      <>
        <em className="cp-ex__unkeyed">{blank}</em>
        {item.scopes?.length ? <small className="cp-ex__uid">{item.scopes.map(scopeLine).join("; ")}</small> : null}
        {why.length ? <small className="cp-ex__uid">Broad scope: {why.map(scopeLine).join("; ")}. The chosen entity is not individually named.</small> : null}
      </>
    );
  }
  return (
    <>
      {why.length ? <small className="cp-ex__uid">Broad scope: {why.map(scopeLine).join("; ")}. The chosen entity is not individually named.</small> : null}
      {first.name ?? <em>{first.withheld ? WITHHELD_TEXT : first.uid}</em>}
      {entities.length > 1 ? <small className="cp-ex__uid"> +{entities.length - 1} more</small> : null}
      {first.uid ? <small className="cp-ex__uid">{item.entity.uids.join(" · ")}</small> : null}
      {item.subject ? <small className="cp-ex__uid">record names: {item.subject}</small> : null}
    </>
  );
}

// ── The table, and the list it becomes on a phone ──────────────────────────

function SortHead({ column, label, sort, onSort, pinned, className }) {
  const on = sort?.by === column;
  const dir = on ? sort.dir : null;
  return (
    <th scope="col" className={`${className ?? ""}${pinned ? " cp-ex__pin" : ""}`} aria-sort={on ? (dir === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className={`cp-ex__sort${on ? " is-on" : ""}`} onClick={() => onSort(column)}>
        {label}
        <span aria-hidden="true">{dir === "asc" ? " ↑" : dir === "desc" ? " ↓" : ""}</span>
      </button>
    </th>
  );
}

export function Rows({ view, items, columns, sort, onSort, onActive, showAmount, entityColumn, contract, openRecord, readOnly = false }) {
  // The scroll container's own width, as a CSS variable, so an expanded
  // record can pin itself to the visible part of a table wider than it.
  // And the pinned columns' own widths, so the name pins exactly where the
  // uid ends: a fixed offset in CSS left a gap a scrolled column showed
  // through.
  const scrollRef = useRef(null);
  const columnsKey = columns.join("|");
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return undefined;
    // BOTH edges, and only where there is something past them. The old
    // version tracked the right edge alone and wrote `data-end="0"` when
    // there was nothing more — which still matched `[data-end]`, so the one
    // selector that could have switched the cue off never did. Presence is
    // the state now, and `scrollEdges` is the single place that decides it;
    // `scrollEdges.test.js` holds it to the last column.
    const edge = () => {
      const wrap = node.parentElement;
      if (!wrap) return;
      const { start, end } = scrollEdges(node);
      wrap.toggleAttribute("data-start", start);
      wrap.toggleAttribute("data-end", end);
    };
    const measure = () => {
      node.style.setProperty("--vw", `${node.clientWidth}px`);
      const more = node.querySelector("th.cp-ex__more");
      const uid = node.querySelector("th.cp-ex__pin--uid");
      node.style.setProperty("--more-w", `${more ? more.getBoundingClientRect().width : 0}px`);
      node.style.setProperty("--uid-w", `${uid ? uid.getBoundingClientRect().width : 0}px`);
      edge();
    };
    measure();
    node.addEventListener("scroll", edge, { passive: true });
    if (typeof ResizeObserver === "undefined") return () => node.removeEventListener("scroll", edge);
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => {
      node.removeEventListener("scroll", edge);
      observer.disconnect();
    };
  }, [columnsKey]);
  const universal = [
    ["entity", "Entity", true],
    ["entity_type", "Entity type"],
    ["collection", "Collection"],
    ["date", "Date"],
    ["observation", "Observation"],
    // "Amount" alone: the basis is written under each value, and a value
    // is shown only where the row's table records one.
    ...(showAmount ? [["amount", "Amount"]] : []),
    ["source", "Source"],
  ];
  const pinned = (c) => c === entityColumn || c === contract?.entity_uid;
  const heads = view === "table" ? columns.map((c) => [c, labelFor(items[0]?.key, c), pinned(c), c === contract?.entity_uid ? " cp-ex__pin--uid" : c === entityColumn && contract?.entity_uid && columns.includes(contract.entity_uid) ? " cp-ex__pin--name" : ""]) : universal;
  return (
    // The wrapper exists for the edge fade: every cell paints its own
    // background, so a gradient on the scroller itself is painted over by
    // the table. It sits outside the scroller, does not scroll, and is what
    // says the table continues; without it the last column sat half-cut
    // against a hard border and read as a rendering fault. The scroller
    // takes keyboard focus, because a scrollable region with no focusable
    // child cannot be reached without a mouse.
    <div className="cp-ex__scrollwrap">
    <div className="cp-ex__scroll" ref={scrollRef} tabIndex={0} role="region" aria-label="Records, scroll sideways for more columns">
      <table className={`cp-ex__table cp-ex__table--${view}`}>
        <thead>
          <tr>
            {readOnly ? null : <th scope="col" className="cp-ex__more"><span className="cp-badge__sr">Open the record</span></th>}
            {heads.map(([column, label, pin, pinClass]) => {
              const className = `cp-ex__c-${column === "amount" || column === contract?.amount ? "amount" : "text"}${pinClass ?? ""}`;
              // A sort control the visitor cannot use is worse than a plain
              // heading: it invites a click that does nothing.
              return readOnly ? (
                <th key={column} scope="col" className={`${className}${pin ? " cp-ex__pin" : ""}`}>{label}</th>
              ) : (
                <SortHead key={column} column={column} label={label} sort={sort} onSort={onSort} pinned={pin} className={className} />
              );
            })}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            return [
              /* THE ROW IS A DOOR, NOT A DRAWER.
                 A click anywhere that is not itself a control opens the
                 record's own page; the first cell carries the explicit link a
                 keyboard and a screen reader use, and the row handler stands
                 down for a click that landed on a link, a button, or a
                 selection the reader is making with the mouse. */
              <tr
                key={item.id}
                data-testid={readOnly ? "stage-record" : "explore-record"}
                data-record-id={item.recordId ?? ""}
                className={`cp-ex__row${item.superseded ? " is-superseded" : ""}${readOnly ? " is-static" : ""}`}
                onClick={readOnly ? undefined : (event) => {
                  if (event.target.closest("a, button, input, label, summary")) return;
                  if (window.getSelection?.().toString()) return;
                  openRecord(item);
                }}
              >
                {readOnly ? null : (
                <td className="cp-ex__more">
                  <Link className="cp-ex__morebtn" to={openRecord.href(item)} onClick={() => openRecord.remember()}>
                    <span aria-hidden="true">&#8594;</span>
                    <span className="cp-badge__sr">Open the full record</span>
                  </Link>
                </td>
                )}
                {view === "table"
                  ? columns.map((column) => (
                    <td key={column} className={`${pinned(column) ? "cp-ex__pin" : ""}${column === contract?.entity_uid ? " cp-ex__pin--uid" : column === entityColumn && contract?.entity_uid && columns.includes(contract.entity_uid) ? " cp-ex__pin--name" : ""}${column === contract?.amount ? " cp-ex__amount" : ""}`}>
                      {column === entityColumn && item.superseded ? <span className="cp-ex__badge">Superseded</span> : null}
                      {column === entityColumn && item.entity.withheld ? <em>{WITHHELD_TEXT}</em> : <Human column={column} value={item.row[column]} contract={contract} item={item} />}
                      {column === entityColumn && item.entity.uid && !columns.includes(contract?.entity_uid) ? <small className="cp-ex__uid">{item.entity.uids.join(" · ")}</small> : null}
                    </td>
                  ))
                  : (
                    <>
                      <td className="cp-ex__pin">
                        {item.superseded ? <span className="cp-ex__badge">Superseded</span> : null}
                        <EntityCell item={item} />
                      </td>
                      <td>{item.entity.type ?? "—"}</td>
                      <td>
                        <button type="button" className="cp-ex__coll" onMouseEnter={() => onActive(item.collection)} onFocus={() => onActive(item.collection)} onClick={() => onActive(item.collection)}>
                          {short(item.collection)}
                        </button>
                      </td>
                      <td className="cp-ex__date">{item.date ?? "—"}</td>
                      <td className="cp-ex__obs"><span className="cp-ex__clamp">{item.observation || "—"}</span></td>
                      {showAmount ? (
                        <td className="cp-ex__amount">
                          {item.amount == null ? "—" : money.format(item.amount)}
                          {item.amount != null && item.amountBasis ? <small className="cp-ex__uid">{item.amountBasis}</small> : null}
                        </td>
                      ) : null}
                      <td>{item.source ? <a href={item.source} target="_blank" rel="noreferrer">Source <span aria-hidden="true">&#8599;</span></a> : <span className="cp-ex__fine">no link</span>}</td>
                    </>
                  )}
              </tr>,
            ];
          })}
        </tbody>
      </table>
    </div>
    </div>
  );
}

/** The same records as compact rows for a phone: who, where, when, what; tap opens the record. */
export function Cards({ items, onActive, openRecord, readOnly = false }) {
  return (
    <ul className="cp-ex__cards">
      {items.map((item) => {
        const inside = (
          <>
            <span className="cp-ex__cardwho">
              {item.superseded ? <span className="cp-ex__badge">Superseded</span> : null}
              <EntityCell item={item} />
            </span>
            <span className="cp-ex__cardmeta">{short(item.collection)} · {item.date ?? "undated"}{item.amount != null ? ` · ${money.format(item.amount)}` : ""}</span>
            <span className="cp-ex__cardobs cp-ex__clamp">{item.observation || "—"}</span>
            {readOnly ? null : <span className="cp-ex__cardgo" aria-hidden="true">&#8594;</span>}
          </>
        );
        return (
          <li key={item.id} data-testid={readOnly ? "stage-record" : "explore-record"} data-record-id={item.recordId ?? ""} className={item.superseded ? "is-superseded" : ""}>
            {/* On the door a card is the record, not a way to it: the
                record's own page is behind the paywall, so it is not a link
                that would bounce a visitor into a sign-in. */}
            {readOnly ? (
              <div className="cp-ex__cardbtn cp-ex__cardbtn--static">{inside}</div>
            ) : (
              <Link
                className="cp-ex__cardbtn"
                to={openRecord.href(item)}
                onClick={() => { openRecord.remember(); onActive(item.collection); }}
              >
                {inside}
              </Link>
            )}
          </li>
        );
      })}
    </ul>
  );
}
