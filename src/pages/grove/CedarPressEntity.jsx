// REVIEW OWNER: Havala
//
// One entity, across the collections.
//
// The record page's companion, and the reason the entity's name on a record
// is a link rather than a string. The review's distinction, 2026-09-14: a
// record page is a TRANSACTION — one funding action, one filing, one award —
// and "the entity's name should link to a separate entity profile that brings
// together its records across collections". These are the two halves of that.
//
// WHAT IT IS ALLOWED TO CLAIM
// Very little, and it says so on its face. The register gives the canonical
// name and the entity's class; the rows come from the same published ten-row
// samples every other surface reads. So the counts here are counts of PREVIEW
// records, never of the collections, and a collection showing nothing means
// the sample did not happen to include this entity — not that Cedar holds
// nothing for it. Anything stronger would need the serving layer this
// repository has not deployed, and a profile that implied it had one would be
// the most misleading page on the site.
//
// A locked collection is not read at all. The shelf is the reader's, and the
// page says how many collections it could not look in.

import { useMemo } from "react";
import { Link, useParams, useSearchParams } from "react-router";

import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import {
  WITHHELD_TEXT,
  explorableCollections,
} from "../../features/grove/explore.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";
import { recordHref } from "../../features/grove/pressRecord.js";
import { PRESS_DATA_PATH, PRESS_METHODS_PATH } from "../../features/grove/pressRoutes.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useRegister } from "../../features/grove/useRegister.js";
import { useNarrow } from "../../features/grove/useNarrow.js";
import { useSampleRows } from "../../features/grove/useSamples.js";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function CedarPressEntity() {
  const { user, loading } = useAuth();
  const narrow = useNarrow();
  const entitled = canReadCedarPress(user);
  const { uid } = useParams();
  const [params] = useSearchParams();
  // Where this profile was opened from, when a record opened it.
  const from = params.get("from") ?? null;
  const register = useRegister();
  useScrollToTop(uid);
  useDocumentTitle(register.byUid.get(uid)?.name ?? "Entity");

  const collections = useMemo(() => explorableCollections(user), [user]);
  // Every flagship the reader's plan opens: one dataset per collection, which
  // is what a collection is to a subscriber.
  const tables = useMemo(
    () => collections.filter((c) => c.open && c.flagship).map((c) => c.flagship),
    [collections],
  );
  const locked = collections.filter((c) => !c.open).length;
  const { rows, missing, loading: samplesLoading } = useSampleRows(tables, register);

  const entity = register.byUid.get(uid) ?? null;
  // The register has loaded and this id is not in it. The page then has no
  // entity to describe records for, and no table to open narrowed to it.
  const unknown = !entity && register.entities.length > 0;
  const mine = useMemo(
    () => rows.filter((item) => item.entity.entities.some((e) => e.uid === uid)),
    [rows, uid],
  );
  // THE SPAN OF WHAT IS VISIBLE, and the names the sources used.
  //
  // Both are derived from rows the page already had. The second is the point
  // of the whole identity layer and the page was throwing it away: a record
  // carries its own subject — the name the SOURCE used — and `explore.js`
  // keeps it only when it differs from the canonical name. So this list is
  // exactly "the other names this entity is filed under", which is what a
  // Cedar id is for, shown rather than asserted.
  const dates = useMemo(
    () => mine.map((item) => item.date).filter(Boolean).sort(),
    [mine],
  );
  const sourceNames = useMemo(() => {
    const seen = new Map();
    for (const item of mine) {
      if (!item.subject) continue;
      const key = item.subject.toUpperCase();
      if (!seen.has(key)) seen.set(key, { name: item.subject, collections: new Set() });
      seen.get(key).collections.add(item.collection);
    }
    return [...seen.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [mine]);

  // Grouped by collection, in the catalog's order, so the profile reads as
  // the shelf does.
  // What the rows on this screen add up to, where they carry money at all.
  // `count` travels with it so the label can never be read as a total for
  // the entity: it is a sum of a preview, and the preview is ten rows a
  // table.
  const shown = useMemo(() => {
    const amounts = mine.filter((item) => typeof item.amount === "number");
    return amounts.length
      ? { total: amounts.reduce((sum, item) => sum + item.amount, 0), count: amounts.length }
      : { total: null, count: 0 };
  }, [mine]);
  const groups = useMemo(() => {
    const byCollection = new Map();
    for (const item of mine) {
      if (!byCollection.has(item.collection)) byCollection.set(item.collection, []);
      byCollection.get(item.collection).push(item);
    }
    return collections
      .filter((c) => byCollection.has(c.entry.id))
      .map((c) => ({ entry: c.entry, items: byCollection.get(c.entry.id) }));
  }, [mine, collections]);

  if (!loading && !entitled) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }

  const notice = samplesLoading
    ? "Reading the published previews…"
    : `Records Cedar Press has resolved to this entity, from the published previews — up to ten sample rows per table, never a count of a release. The name each source used stays visible.${locked ? ` ${locked} more collections open on Cedar Press+.` : ""}`;
  const name = entity?.withheld ? WITHHELD_TEXT : entity?.name ?? null;

  /**
   * FOUR DERIVED FIGURES, AND WHERE THEY GO ON A PHONE.
   *
   * They are a summary OF the records, and on a 390x664 screen they stood
   * 125px tall between the reader and the first one — two-column stacks of
   * uppercase mono labels over single digits, with "Visible span" wrapping to
   * two lines. Measured with the private-preview notice in place, the first
   * record sat 177px below the fold.
   *
   * This page has already settled that argument once. The identity evidence
   * moved below the ledger with the note "a phone settled it ... above the
   * ledger it pushed the first record off the first screen, which is the one
   * thing this page is for", and the same sentence is true of these figures.
   * So they move the same way and on the same breakpoint, rather than being
   * shrunk until nobody can read them: nothing is hidden and no word changes.
   * They are simply not what a reader opened this page for.
   */
  const glance = groups.length ? (
    <dl className="cp-ent__glance" data-testid="entity-glance">
      <div>
        <dt>In collections</dt>
        <dd>{groups.length}</dd>
      </div>
      <div>
        <dt>Preview records</dt>
        <dd>{mine.length}</dd>
      </div>
      {dates.length ? (
        <div>
          <dt>Visible span</dt>
          <dd>{dates[0] === dates[dates.length - 1] ? dates[0] : `${dates[0]} to ${dates[dates.length - 1]}`}</dd>
        </div>
      ) : null}
      {/* Only where the rows carry money. A sum of what is on the screen,
          labelled as that and nothing wider: the preview is ten rows a table,
          so this is never a total for the entity and the label may not let
          anybody read it as one. */}
      {shown.total != null ? (
        <div>
          <dt>{shown.count === 1 ? "On this row" : `On these ${shown.count} rows`}</dt>
          <dd>{money.format(shown.total)}</dd>
        </div>
      ) : null}
    </dl>
  ) : null;

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page cp-ent">
        <PressMast section="data" />

        <div className="cp-rec__bar">
          {/* Back to the record this profile was opened from, when it was:
              a reader who arrived from one transaction is usually going back
              to it. Otherwise, back to the collections. */}
          {from ? (
            <Link className="cp-rec__back" to={from}>
              <span aria-hidden="true">&#8592;</span> Back to the record
            </Link>
          ) : (
            <Link className="cp-rec__back" to={PRESS_DATA_PATH}>
              <span aria-hidden="true">&#8592;</span> All collections
            </Link>
          )}
          {unknown ? null : (
            <Link className="cp-rec__walkbtn" to={`${PRESS_DATA_PATH}?e=${encodeURIComponent(uid)}`}>
              View in table <span aria-hidden="true">&#8594;</span>
            </Link>
          )}
        </div>

        {/* IDENTITY, THEN RECORDS.
            Review, 2026-09-15: "the profile's purpose is to get users to an
            entity's related records. On mobile, none are visible in the
            captured first screen. Keep the name, type, and ID compact,
            followed by a short preview notice and the collection results."
            The three-figure strip went with it: "Collections read" described
            a loading operation rather than the entity, and two of the three
            figures were one sentence between them. */}
        {/* THE IDENTITY PANEL.
            Owner, 2026-09-20: "the profile page from Native Entity just
            looks like text. Like at least you can put cards or make it have
            more intentionality behind it."

            It was five stacked paragraphs — eyebrow, name, ids, a sentence
            about what the page is, a sentence about what the counts mean —
            and then a separate strip of three figures. One panel now: who
            this is on the left, what is known about them on the right, and
            the marks of the collections they appear in underneath, so the
            shape of an entity's footprint is visible before a single row is
            read. Nothing is invented: every figure is derived from the rows
            on this screen and says what it counts. */}
        <header className="cp-rec__head cp-ent__head" data-testid="entity-head">
          <div className="cp-ent__who">
            <p className="cp-ent__eyebrow">Cedar entity profile</p>
            <h1 className="cp-rec__name">
              {name ?? (register.entities.length ? "No entity with that Cedar id" : "Opening the entity…")}
            </h1>
            <p className="cp-rec__ids">
              <span className="cp-rec__uid"><code>{uid}</code></span>
              {entity?.type ? <span className="cp-rec__type">{entity.type}</span> : null}
            </p>
            {groups.length ? (
              <ul className="cp-ent__marks" aria-label="Collections this entity appears in">
                {groups.map(({ entry }) => (
                  <li key={entry.id}>
                    <Link to={`${PRESS_DATA_PATH}?c=${entry.id}&e=${encodeURIComponent(uid)}`} title={entry.name}>
                      <span className="cp-ent__markic" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
                      {entry.short || entry.name}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>

          {/* On a wide screen the glance sits with the identity, where a
              summary belongs. On a phone it is rendered after the ledger
              instead — same block, same words, further down. See `glance`. */}
          {narrow ? null : glance}

          {/* THE CAVEAT, AND WHAT A PHONE HAS ROOM FOR.
              It is a real caveat and it is not dropped: a reader must not
              take "2 preview records" for this entity's whole footprint. But
              five lines of it above the first record, on a page whose
              purpose the 2026-09-15 review already stated is "to get users
              to an entity's related records", is the caveat winning. On a
              phone it is a disclosure; the figures above it carry the word
              "preview" either way. */}
          {unknown ? null : narrow ? (
            <details className="cp-rec__fine cp-ent__notice cp-ent__notice--fold">
              <summary>What these records are</summary>
              <p>{notice}</p>
            </details>
          ) : (
            <p className="cp-rec__fine cp-ent__notice">{notice}</p>
          )}
          {missing.length ? (
            <p className="cp-rec__fine">
              Not reachable right now: {missing.map((key) => PRESS_CATALOG_BY_ID[key.split("/")[0]]?.short ?? key).join(", ")}.
            </p>
          ) : null}
        </header>

        {samplesLoading && !groups.length ? (
          <p className="cp-rec__fine cp-ent__empty">Reading the published samples…</p>
        ) : groups.length ? (
          <div className="cp-ent__groups">
            {groups.map(({ entry, items }) => (
              <section className="cp-ent__group" key={entry.id} aria-label={entry.name}>
                {/* THE COLLECTION'S NAME IS A WAY INTO IT.
                    This profile reads up to ten sample rows per table; the
                    collection holds the release. A reader who has just seen
                    three of this entity's awards and wants the rest was
                    being shown the collection's name as a label. It is a
                    link now, carrying BOTH the collection and the entity, so
                    it opens the table already narrowed to what this heading
                    is about rather than on the collection's first page. */}
                <header className="cp-ent__ghead">
                  <span className="cp-ent__gic" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
                  <h2>
                    <Link className="cp-ent__glink" to={`${PRESS_DATA_PATH}?c=${entry.id}&e=${encodeURIComponent(uid)}`}>
                      {entry.name} <span aria-hidden="true">&#8594;</span>
                    </Link>
                  </h2>
                  <span className="cp-ent__gn">{items.length} preview record{items.length === 1 ? "" : "s"}</span>
                </header>
                <ul className="cp-ent__list">
                  {items.map((item) => (
                    <li key={item.id}>
                      {/* A ledger row, not a card: date, what, amount, in
                          the same columns down the page, so a reader can
                          read an entity's activity by scanning one edge. */}
                      <Link className="cp-ent__row" to={recordHref({ key: item.key, recordId: item.recordId, index: item.index })}>
                        <span className="cp-ent__rowdate">{item.date ?? "undated"}</span>
                        <span className="cp-ent__rowwhat">
                          {item.observation || "—"}
                          {/* The source's own name for this entity, on the
                              record that used it. */}
                          {item.subject ? <small className="cp-ent__rowsrc">named {item.subject}</small> : null}
                        </span>
                        <span className="cp-ent__rowamt">{item.amount != null ? money.format(item.amount) : ""}</span>
                        <span className="cp-ent__rowgo" aria-hidden="true">&#8594;</span>
                      </Link>
                    </li>
                  ))}
                </ul>
                {/* The card's own way out. The heading is a link too, but a
                    reader who has just finished the rows is at the bottom of
                    the card, and a card that ends in a dead edge ends the
                    page as far as they are concerned. */}
                <Link className="cp-ent__gmore" to={`${PRESS_DATA_PATH}?c=${entry.id}&e=${encodeURIComponent(uid)}`}>
                  All of this entity&rsquo;s {entry.short || entry.name} records <span aria-hidden="true">&#8594;</span>
                </Link>
              </section>
            ))}
          </div>
        ) : (
          <p className="cp-rec__fine cp-ent__empty" data-testid="entity-empty">
            No record in the published previews names this entity. That does not establish whether
            the releases hold records for it: each table ships up to ten sample rows, and this page
            reads those.
          </p>
        )}

        {/* The glance, on a phone: after the ledger, for the reason above it
            in `glance`. On a wide screen this renders nothing, because the
            header already carried it. */}
        {narrow ? glance : null}

        {/* WHY THESE RECORDS ARE CONNECTED — after them, not before.
            The brief's own order puts the records second and the identity
            evidence fourth, and a phone settled it: the block is six lines
            of navy, and above the ledger it pushed the first record off the
            first screen, which is the one thing this page is for.
            A Cedar id is a claim that several source names are one
            organization, and until now the page made that claim silently.
            Every name here came off a record in the previews above; none is
            written. When the sources all used the canonical name there is
            nothing to show, and the block does not render — an empty
            "aliases" panel would imply a check nobody ran. */}
        {sourceNames.length ? (
          <section className="cp-ent__ident" aria-label="Names in the sources" data-testid="entity-names">
            <h2 className="cp-ent__identhead">Filed under these names</h2>
            <p className="cp-rec__fine">
              Each of these is a name a source used for this entity in the records below. Cedar
              resolves them to <b>{name}</b> and keeps the source&rsquo;s own wording on the record.
            </p>
            <ul className="cp-ent__names">
              {sourceNames.map((item) => (
                <li key={item.name}>
                  <span className="cp-ent__namesrc">{item.name}</span>
                  <span className="cp-ent__namein">
                    {[...item.collections]
                      .map((id) => PRESS_CATALOG_BY_ID[id]?.short ?? id)
                      .join(", ")}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <p className="cp-rec__fine cp-ent__foot">
          <Link className="cp-m__more" to={PRESS_METHODS_PATH}>
            How a record reaches its entity <span aria-hidden="true">&#8594;</span>
          </Link>
        </p>

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
