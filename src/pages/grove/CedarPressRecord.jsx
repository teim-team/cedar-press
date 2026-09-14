// REVIEW OWNER: Havala
//
// One record, on a page of its own.
//
// ============================================================================
// WHY THIS REPLACED THE EXPANDED ROW (review, 2026-09-14)
// ============================================================================
// "The expanded row is effectively an entire record page squeezed into a
// table, and the explanations give every field equal visual weight."
//
// Four things follow from that, and they are the whole design:
//
// 1. IT IS A TRANSACTION PAGE, NOT AN ENTITY PAGE. The row is one funding
//    action, one award, one filing. So the page answers the questions a row
//    raises — who received it, what it funded, how much, when, and where the
//    evidence is — and the entity's NAME is a link to the entity's own page,
//    which is the thing that gathers its records across collections.
//
// 2. THE FIRST SCREEN IS THE ANSWER. The amount at the size of the answer,
//    the collection's own one-line description of the row under it, and the
//    date. Everything else is below it, and most of it is folded.
//
// 3. NO PARAGRAPH UNDER EVERY VALUE. The codebook's definitions are real and
//    worth keeping; printed under all thirty-four values they made every
//    field as loud as every other. They are behind one control now — "Field
//    definitions" — which turns them on for the whole page at once, and each
//    label still carries its definition as a title for a pointer.
//
// 4. BACK TO RESULTS MEANS BACK. The filters, the sort, the page and the
//    scroll position. The cut travels in `from` and the scroll waits in
//    session storage (features/grove/pressRecord.js); previous and next walk
//    the reader's own ordering, so a researcher can read six transactions
//    without returning to the table between them.
//
// WHAT THIS PAGE MAY SAY
// The same rule as everywhere else: nothing here is written about a record.
// The labels and definitions are the codebook's, the roles are the table's
// declared contract, the resolution sentence is the collection's own
// `linkage`, the citation is `collectionCitation` — the same function the
// download embeds — and the adjusted amount is a column the file carries. A
// field this page cannot explain is shown as the file spells it.

import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import {
  WITHHELD_TEXT,
  codebookColumns,
  codebookFor,
  contractFor,
  decodeCut,
  explorableCollections,
  filterRows,
  labelFor,
  meaningFor,
  sortRows,
} from "../../features/grove/explore.js";
import { collectionCitation } from "../../features/grove/collection.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";
import { releaseFor } from "../../features/grove/pressReleases.js";
import {
  findRecord,
  neighbours,
  readRecordParams,
  realDollars,
  recordHref,
  resultsHref,
} from "../../features/grove/pressRecord.js";
import { PRESS_METHODS_PATH, PRESS_RECORD_PATH, pressEntityPath } from "../../features/grove/pressRoutes.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useRegister } from "../../features/grove/useRegister.js";
import { useSampleRows } from "../../features/grove/useSamples.js";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

/** A JSON array cell as a list of words, or null when the cell is not one. */
function readJsonList(text) {
  if (!/^\[/.test(text)) return null;
  try {
    const parsed = JSON.parse(text);
    if (!Array.isArray(parsed)) return null;
    return parsed.map((p) => (p == null ? "unresolved" : typeof p === "object" ? (p.url ?? JSON.stringify(p)) : String(p)));
  } catch {
    return null;
  }
}

/** One value, as a reader reads it. The table's own formatter, unchanged. */
function Value({ column, value, contract, item }) {
  if (value === "" || value == null) return <span className="cp-rec__blank">not recorded</span>;
  const text = String(value);
  if (/^https?:\/\/\S+$/i.test(text)) {
    return (
      <a href={text} target="_blank" rel="noreferrer">
        {text.replace(/^https?:\/\/(www\.)?/, "").slice(0, 72)}{text.length > 80 ? "…" : ""}
      </a>
    );
  }
  if (contract?.amount === column || /(_usd|_amt|obligations|_amount|amount_usd)$/i.test(column) || /^(income|expenses|spend)_/i.test(column)) {
    const n = Number(text.replace(/[$,\s]/g, ""));
    if (Number.isFinite(n)) return money.format(n);
  }
  if (/^\d{4}-\d{2}-\d{2}T/.test(text)) return text.slice(0, 10);
  const yesNo = /\(yes or no\)/.test(meaningFor(item?.key, column) ?? "") || /^(is_|has_|self_|reported_)|_flag$/.test(column);
  if (yesNo && /^(0|1|Y|N)$/i.test(text)) return /^(1|Y)$/i.test(text) ? "yes" : "no";
  if (text.includes("|") && !/^https?:/.test(text)) return text.split("|").map((p) => p.trim()).filter(Boolean).join(", ");
  // A JSON array cell (the approved schema's plural block and lists) reads as
  // a list, an unresolved member as "unresolved", an object by its url. The
  // parse is kept out of the return: JSX built inside a try/catch is not
  // covered by it, since the component renders after the block has exited.
  const list = readJsonList(text);
  if (list) return list.length ? list.join(", ") : <span className="cp-rec__blank">not recorded</span>;
  return text;
}

/**
 * A block of fields, two columns on a wide screen.
 *
 * `plain` decides whether the label is the codebook's English or the file's
 * column name — the technical block shows the file's, because a reader in
 * there is looking at the file. `definitions` is the page-wide switch: off,
 * the definition is the label's title and nothing else.
 */
function Fields({ columns, item, contract, plain = true, definitions = false }) {
  return (
    <dl className="cp-rec__fields">
      {columns.map((column) => {
        const meaning = plain ? meaningFor(item.key, column) : null;
        const blank = item.row[column] === "" || item.row[column] == null;
        return (
          <div key={column} className={blank ? "is-blank" : ""}>
            <dt title={meaning ?? undefined}>{plain ? labelFor(item.key, column) : column}</dt>
            <dd><Value column={column} value={item.row[column]} contract={contract} item={item} /></dd>
            {definitions && meaning ? <dd className="cp-rec__mean">{meaning}</dd> : null}
          </div>
        );
      })}
    </dl>
  );
}

/**
 * The rest of a record, in groups a reader can choose between.
 *
 * Review, 2026-09-15: "'Show 54 more fields' risks recreating the original
 * overwhelming panel in one click. Group those fields into identifiers,
 * classifications, geography, and financial details so users can open the
 * relevant group."
 *
 * The rules are by column name and are deliberately few, because a wrong
 * group is a cosmetic mistake and a missing field is not: anything the rules
 * do not recognise lands in "Other fields", which is shown like the rest.
 * Order matters — a state FIPS code is geography before it is an identifier.
 */
const FIELD_GROUPS = [
  { id: "geography", label: "Geography", test: /(^geo_|_fips$|state|city|county|place|zip|country|region|district)/i },
  { id: "financial", label: "Financial details", test: /(usd|amount|obligat|loan|subsid|revenue|spend|deflator|dollar|price|value)/i },
  { id: "identifiers", label: "Identifiers", test: /(_id$|_ids$|^id$|_key$|_uid$|uei|duns|\bein\b|^ein$|cage|fain|_number$|naics|cfda)/i },
  { id: "classifications", label: "Classifications and status", test: /(type|class|category|status|flag|method|basis|tier|rule|description|stage|role|confidence)/i },
];

function groupFields(columns) {
  const groups = FIELD_GROUPS.map((group) => ({ ...group, columns: [] }));
  const other = { id: "other", label: "Other fields", columns: [] };
  for (const column of columns) {
    const group = groups.find((candidate) => candidate.test.test(column));
    (group ?? other).columns.push(column);
  }
  return [...groups, other].filter((group) => group.columns.length);
}

/** Copy, with the prompt fallback for a browser that refuses the clipboard. */
function CopyButton({ text, label, done = "Copied", className = "cp-rec__copy" }) {
  const [copied, setCopied] = useState(false);
  if (!text) return null;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // The Clipboard API is absent on a non-secure origin and rejected
      // outright under some permission policies. A prompt is still a copy.
      window.prompt(`Copy ${label.toLowerCase()}`, text);
    }
  };
  return (
    <button type="button" className={className} onClick={copy}>
      {copied ? done : label}
    </button>
  );
}

/** Previous and next in the reader's own ordering, and where they are in it. */
function Walk({ place, from, className }) {
  if (place.at < 0) return null;
  const href = (item) => recordHref({ key: item.key, recordId: item.recordId, index: item.index, from });
  return (
    <nav className={className} aria-label="Records in this result">
      {place.previous ? (
        <Link className="cp-rec__walkbtn" to={href(place.previous)}>
          <span aria-hidden="true">&#8592;</span> Previous
        </Link>
      ) : (
        <span className="cp-rec__walkbtn is-off" aria-hidden="true">&#8592; Previous</span>
      )}
      <span className="cp-rec__walkat">Record {place.at + 1} of {place.of}</span>
      {place.next ? (
        <Link className="cp-rec__walkbtn" to={href(place.next)}>
          Next <span aria-hidden="true">&#8594;</span>
        </Link>
      ) : (
        <span className="cp-rec__walkbtn is-off" aria-hidden="true">Next &#8594;</span>
      )}
    </nav>
  );
}

export default function CedarPressRecord() {
  const { user, loading, logout } = useAuth();
  const entitled = canReadCedarPress(user);
  const [params] = useSearchParams();
  const search = params.toString();
  // One object per query, so everything below can depend on it rather than on
  // a fresh object built each render.
  const asked = useMemo(() => readRecordParams(search), [search]);
  const register = useRegister();
  const [definitions, setDefinitions] = useState(false);
  const [showRest, setShowRest] = useState(false);
  useScrollToTop(search);

  const collections = useMemo(() => explorableCollections(user), [user]);
  const collectionId = asked.key ? asked.key.split("/")[0] : null;
  const collection = collections.find((c) => c.entry.id === collectionId) ?? null;
  const table = collection?.tables.find((t) => t.key === asked.key) ?? null;
  const open = collection ? collection.open : false;
  const tables = useMemo(() => (table && open ? [table] : []), [table, open]);
  const { rows, missing, loading: samplesLoading } = useSampleRows(tables, register);

  // The reader's own ordering: the cut they came from, applied to this
  // table's rows. A cut naming other collections narrows nothing here — the
  // rows are this table's — so previous and next stay this table's records in
  // the order the table showed them.
  const cut = useMemo(() => decodeCut(asked.from), [asked]);
  // `item.index` is the row's position in the table's own sample, set by
  // `universalRows`. It is how a table that declares no id column is
  // addressed, so it means the same thing under every cut — a position in a
  // filtered list would make a link resolve to a different record as soon as
  // the filters changed.
  const ordered = useMemo(
    () => sortRows(filterRows(rows, cut, register), cut.sort),
    [rows, cut, register],
  );
  const item = findRecord(rows, asked);
  // A record the cut filters out is still a record, and its page still opens;
  // there is simply no "next" in a result it is not part of.
  const place = item ? neighbours(ordered, item.id) : { at: -1, of: ordered.length, previous: null, next: null };

  const entry = collectionId ? PRESS_CATALOG_BY_ID[collectionId] ?? null : null;
  const contract = asked.key ? contractFor(asked.key) : null;
  const codebook = asked.key ? codebookFor(asked.key) : null;
  const release = collectionId ? releaseFor(collectionId) : null;
  const citation = collectionId
    ? collectionCitation(collectionId, new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }))
    : null;

  const title = item
    ? `${item.entity.name ?? item.recordId ?? "Record"} · ${entry?.short ?? entry?.name ?? "Record"}`
    : "Record";
  useDocumentTitle(title);

  if (!loading && !entitled) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }

  const back = resultsHref(asked.from);
  // The profile's "Back to the record" needs to know which record: this one,
  // with the cut it was opened from, so the whole chain survives.
  const hereHref = `${PRESS_RECORD_PATH}?${search}`;
  const profileHref = (uid) => `${pressEntityPath(uid)}?from=${encodeURIComponent(hereHref)}`;
  const row = item?.row ?? {};
  const amount = item?.amount ?? null;
  const real = item && contract?.amount ? realDollars(row, contract.amount) : null;
  const shownInHead = new Set([contract?.entity_uid, contract?.entity_name, contract?.entity_type].filter(Boolean));
  // Shown once. Review, 2026-09-15: "fiscal year appears in the summary and
  // again under details, as does the recorded recipient." The summary now
  // carries the money, the date and the one-line observation; the identity
  // line under it carries the recorded name; the details carry everything
  // else the owner declared, including the fiscal year.
  const shownInSummary = new Set([contract?.amount, contract?.date, contract?.subject, ...(contract?.observation ?? [])].filter(Boolean));
  const columns = item ? Object.keys(row) : [];
  // THE OWNER'S DECLARED VIEW IS THE FIRST SCREEN.
  // `default_columns` is the reviewed selection recorded in
  // docs/PUBLIC_DATASET_SPEC_2026-09-05.md — the same seven the table opens
  // on. Everything else the codebook knows is the rest of the record, folded;
  // everything the codebook does not know is technical, folded under that. A
  // table with no declared view falls back to the codebook's own order.
  const declared = (contract?.default_columns ?? []).filter((c) => columns.includes(c));
  const listed = asked.key ? codebookColumns(asked.key, columns) : [];
  // How THIS row reached its entity, from the table's own declaration
  // (`attribution_columns` in data/cedar/explore.overrides.json). These are
  // evidence, not fields to browse: they are shown in the evidence section
  // and taken out of the details, which is also what takes a raw value like
  // `cedar_neid` out of the first screen.
  const attribution = (contract?.attribution_columns ?? [])
    .filter((c) => columns.includes(c) && String(row[c] ?? "").trim());
  const attributionSet = new Set(attribution);
  const spoken = (c) => !shownInHead.has(c) && !shownInSummary.has(c) && !attributionSet.has(c);
  const declaredDetail = (declared.length ? declared : listed.slice(0, 8)).filter(spoken);
  // A DECLARED VIEW CAN BE THIN ONCE THE SUMMARY HAS TAKEN ITS SHARE.
  //
  // Federal Funding declares seven columns; the summary carries three of
  // them, the identity line a fourth and the evidence section a fifth, which
  // left "Record details" holding a fiscal year on its own. So the block is
  // topped up from the codebook's own order, skipping two kinds of column:
  // a long source key (the review: "long transaction and award IDs belong in
  // the additional details") and a bare flag, which is a classification
  // rather than a detail. Both are still one click away, in their groups.
  const LONG_KEY = /(_key$|_id$|_uid$|unique)/i;
  const topUp = listed.filter((c) => {
    if (!spoken(c) || declaredDetail.includes(c)) return false;
    if (/_flag$/.test(c)) return false;
    const text = String(row[c] ?? "");
    return !(LONG_KEY.test(c) && text.length >= 20);
  });
  const detail = declaredDetail.length >= 6
    ? declaredDetail
    : [...declaredDetail, ...topUp].slice(0, 6);
  const detailSet = new Set([...detail, ...shownInHead, ...shownInSummary, ...attributionSet]);
  const rest = listed.filter((c) => !detailSet.has(c));
  const known = new Set([...detailSet, ...rest]);
  const technical = columns.filter((c) => !known.has(c));
  // Everything that is not the declared view, in groups rather than one wall.
  const groups = groupFields([...rest, ...technical]);
  const moreCount = rest.length + technical.length;

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page cp-rec">
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="data" />

        <div className="cp-rec__bar">
          <Link className="cp-rec__back" to={back}>
            <span aria-hidden="true">&#8592;</span> Back to results
          </Link>
          <Walk place={place} from={asked.from} className="cp-rec__walk" />
        </div>

        {!item ? (
          <section className="cp-rec__empty" data-testid="record-empty">
            <h1 className="cp-rec__name">
              {samplesLoading || (!rows.length && !missing.length && open && table)
                ? "Opening the record…"
                : "That record is not in this preview."}
            </h1>
            <p>
              {!asked.key || !collection
                ? "This link does not name a collection Cedar Press carries."
                : !open
                  ? `${entry?.name ?? "This collection"} is not on your plan, so its records do not open here.`
                  : !table
                    ? "This link names a table that has no published preview."
                    : samplesLoading
                      ? "Reading the published sample."
                      : "Each published table ships up to ten sample rows, and this viewer reads those. A record that is in the release may not be in the sample."}
            </p>
            <p>
              <Link className="cp-m__more" to={back}>Back to results <span aria-hidden="true">&#8594;</span></Link>
            </p>
          </section>
        ) : (
          <>
            {/* THE TRANSACTION, THEN WHO IT BELONGS TO.
                Review, 2026-09-15: "on mobile, users encounter the full
                header, back button, previous/next controls, collection
                label, entity name, recorded name, ID, entity type,
                attribution explanation, entity-profile link, and 'What one
                row is' explanation before reaching the amount. The $500,000,
                program, and date should appear immediately beneath the entity
                name. That is the transaction being reviewed."
                So the summary sits directly under the name, and the
                identifiers that used to stand between them are underneath it.
                The codebook's definition of a row came off the opening view
                entirely; it is in the evidence section, where a reader
                checking what they are citing will look. */}
            <header className="cp-rec__head" data-testid="record-head">
              <span className="cp-rec__kind">
                <span className="cp-rec__kindic" aria-hidden="true">{COLLECTION_ICONS[collectionId] ?? null}</span>
                {entry?.name ?? collectionId}
              </span>
              {/* THE CANONICAL NAME, ONCE, PROMINENTLY. What the source
                  system spelled goes underneath in smaller type, because the
                  whole point of the collection is that those are the same
                  organization and one of the two is the one to cite. */}
              <h1 className="cp-rec__name">
                {item.entity.uid && item.entity.name ? (
                  <Link to={profileHref(item.entity.uid)}>{item.entity.name}</Link>
                ) : item.entity.withheld ? (
                  <em>{WITHHELD_TEXT}</em>
                ) : (
                  item.entity.name ?? item.subject ?? "No entity named on this record"
                )}
              </h1>
              {item.superseded ? (
                <p className="cp-rec__superseded">
                  <b>Superseded.</b> A later version replaces this record
                  {item.replacement?.url ? <>: <a href={item.replacement.url} target="_blank" rel="noreferrer">{item.replacement.id}</a></> : item.replacement?.id ? <>: {item.replacement.id}</> : null}.
                </p>
              ) : null}
            </header>

            {/* THE ANSWER, AT THE SIZE OF THE ANSWER. */}
            <section className="cp-rec__sum" aria-label="Summary" data-testid="record-summary">
              {amount != null ? (
                <div className="cp-rec__figure">
                  <p className="cp-rec__fig">{money.format(amount)}</p>
                  <p className="cp-rec__figcap">{item.amountBasis ?? contract?.amount_label ?? labelFor(item.key, contract?.amount)}</p>
                  {/* The original figure stays primary. The adjusted one is
                      the file's own column and names its price year, because
                      "in real dollars" without a year is not a figure. */}
                  {real ? (
                    <p className="cp-rec__real">
                      {money.format(real.value)} <span>in {real.year} dollars</span>
                    </p>
                  ) : null}
                </div>
              ) : null}
              <div className="cp-rec__what">
                {item.observation ? <p className="cp-rec__obs">{item.observation}</p> : null}
                <dl className="cp-rec__key">
                  {contract?.date && row[contract.date] ? (
                    <div>
                      <dt>{labelFor(item.key, contract.date)}</dt>
                      <dd><Value column={contract.date} value={row[contract.date]} contract={contract} item={item} /></dd>
                    </div>
                  ) : null}
                  <div>
                    <dt>Collection</dt>
                    <dd>
                      <Link to={`/data?c=${collectionId}`}>{entry?.name ?? collectionId}</Link>
                    </dd>
                  </div>
                </dl>
              </div>
            </section>

            {/* Who the transaction belongs to, under it: the name the source
                spelled, the Cedar id it resolved to, and the way to that
                entity's own page. */}
            <p className="cp-rec__ids" data-testid="record-identity">
              {item.subject ? <span className="cp-rec__as">Recorded as <b>{item.subject}</b></span> : null}
              {item.entity.uid ? (
                <span className="cp-rec__uid">
                  <code>{item.entity.uid}</code>
                  <CopyButton text={item.entity.uid} label="Copy" />
                </span>
              ) : (
                <span className="cp-rec__fine">Not linked to a Cedar entity on this row.</span>
              )}
              {item.entity.type ? <span className="cp-rec__type">{item.entity.type}</span> : null}
              {item.entity.uid ? (
                <Link className="cp-rec__profile" to={profileHref(item.entity.uid)}>
                  View entity profile <span aria-hidden="true">&#8594;</span>
                </Link>
              ) : null}
            </p>

            <section className="cp-rec__block" aria-label="Record details">
              <div className="cp-rec__blockhead">
                <h2>Record details</h2>
                {/* One switch for the whole page, rather than a paragraph
                    under every value. */}
                <button
                  type="button"
                  className={`cp-rec__toggle${definitions ? " is-on" : ""}`}
                  aria-pressed={definitions}
                  onClick={() => setDefinitions((on) => !on)}
                  data-testid="record-definitions"
                >
                  {definitions ? "Hide field definitions" : "Field definitions"}
                </button>
              </div>
              {detail.length ? (
                <Fields columns={detail} item={item} contract={contract} definitions={definitions} />
              ) : (
                <p className="cp-rec__fine">This table declares no reviewed field selection; everything it carries is below.</p>
              )}
            </section>

            {rest.length || technical.length ? (
              <section className="cp-rec__block" aria-label="Additional details">
                <div className="cp-rec__blockhead">
                  <h2>Additional details</h2>
                  <button
                    type="button"
                    className={`cp-rec__toggle${showRest ? " is-on" : ""}`}
                    aria-expanded={showRest}
                    onClick={() => setShowRest((on) => !on)}
                    data-testid="record-more"
                  >
                    {showRest ? "Hide" : `Show ${moreCount} more fields`}
                  </button>
                </div>
                {showRest ? (
                  /* In groups, not one list of fifty-four: a reader opening
                     this wants geography, or the identifiers, or the loan
                     fields — not all of them at once. Each group opens on its
                     own; the codebook's labels are used where it knows the
                     column and the file's own name where it does not. */
                  <div className="cp-rec__groups">
                    {groups.map((group) => (
                      <details className="cp-rec__group" key={group.id}>
                        <summary>
                          {group.label} <span className="cp-rec__groupn">{group.columns.length}</span>
                        </summary>
                        <Fields
                          columns={group.columns}
                          item={item}
                          contract={contract}
                          plain={group.id !== "other"}
                          definitions={definitions}
                        />
                      </details>
                    ))}
                  </div>
                ) : (
                  <p className="cp-rec__fine">
                    {groups.map((group) => group.label.toLowerCase()).join(", ")} — every column the
                    release carries for this row.
                  </p>
                )}
              </section>
            ) : null}

            {/* WHERE THE EVIDENCE IS.
                Review, 2026-09-15: "'How it reached the entity' contains a
                generic paragraph about subsidiaries, housing authorities, and
                consortia. That does not establish how this particular
                recipient was linked to the Yakama Nation. Where supported,
                show the specific attribution basis and its evidence. If that
                information is unavailable, say so briefly. General matching
                methodology can stay behind a link."
                So the section is this record's own evidence: the document it
                came from, the columns THIS row carries about how it was
                attributed, and a citation. The collection's general rule is a
                link, and the internal table name and transaction key moved
                into the additional details with the other identifiers. */}
            <section className="cp-rec__block cp-rec__prov" aria-label="Source and methodology">
              <div className="cp-rec__blockhead"><h2>Source and evidence</h2></div>
              <div className="cp-rec__provgrid">
                <div>
                  <span className="cp-rec__cap">The document</span>
                  {item.source ? (
                    <a href={item.source} target="_blank" rel="noreferrer">Open the source record <span aria-hidden="true">&#8599;</span></a>
                  ) : (
                    <span className="cp-rec__fine">This row&rsquo;s table carries no per-record link.</span>
                  )}
                  <span className="cp-rec__fine">
                    {entry?.short ?? collectionId}
                    {/* `cadence` is already a sentence ("Updated monthly"). */}
                    {release ? ` · release ${release.version} · ${release.cadence.toLowerCase()}` : ""}
                  </span>
                </div>
                <div>
                  <span className="cp-rec__cap">How this record was matched</span>
                  {attribution.length ? (
                    <dl className="cp-rec__match">
                      {attribution.map((column) => (
                        <div key={column}>
                          <dt title={meaningFor(item.key, column) ?? undefined}>{labelFor(item.key, column)}</dt>
                          <dd><Value column={column} value={row[column]} contract={contract} item={item} /></dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    <span className="cp-rec__fine">
                      This table does not record a per-row basis for its match.
                    </span>
                  )}
                  <Link className="cp-rec__more" to={`${PRESS_METHODS_PATH}#m-linkage`}>
                    How Cedar matches records <span aria-hidden="true">&#8594;</span>
                  </Link>
                </div>
              </div>
              {codebook ? (
                <p className="cp-rec__fine cp-rec__rowis">
                  <b>One row</b> {codebook.row}
                </p>
              ) : null}
              {citation ? (
                <div className="cp-rec__cite">
                  <span className="cp-rec__cap">Cite it</span>
                  <code>{citation}</code>
                  <CopyButton text={citation} label="Copy citation" className="cp-rec__citebtn" />
                </div>
              ) : null}
              {/* One notice, once. */}
              <p className="cp-rec__fine cp-rec__preview">
                Preview: one of up to ten sample rows published for this table.
              </p>
            </section>

            <div className="cp-rec__foot">
              <Link className="cp-rec__back" to={back}>
                <span aria-hidden="true">&#8592;</span> Back to results
              </Link>
              <CopyButton
                text={typeof window === "undefined" ? "" : window.location.href}
                label="Copy link to this record"
                done="Link copied"
                className="cp-rec__linkbtn"
              />
              <Walk place={place} from={asked.from} className="cp-rec__walk" />
            </div>
          </>
        )}

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
