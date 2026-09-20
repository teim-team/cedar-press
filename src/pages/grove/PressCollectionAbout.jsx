// The collection profile: what this collection is, how it was built, and
// where it stops.
//
// WHAT IT REPLACES. "About this collection" opened a `<details>` in the pane
// head holding four lines of prose. That is a tooltip, not a profile, and it
// could not be linked to — a reader who wanted to send somebody the method
// behind a figure had nothing to send.
//
// So it is a deep-linkable panel: `?c=<id>&about=1`, which keeps the cut
// beside it, so closing the panel returns the reader to exactly the table
// they opened it from. A side sheet on a wide screen and the whole screen on
// a phone, per the brief.
//
// NOTHING HERE IS WRITTEN. Every field comes from a file the release
// produced: the descriptor (`collections.manifest.json` by way of
// `collection.js`), the catalog, the codebook, and the release ledger. A
// profile that paraphrased its collection would drift from it the first time
// a release moved, and the whole point of the page is to be the thing a
// reader checks a figure against.
import { useEffect, useRef } from "react";
import { Link } from "react-router";

import {
  LAUNCH_COLLECTION,
  collectionCedarFacts,
  collectionTables,
} from "../../features/grove/collection.js";
import { codebookFor } from "../../features/grove/explore.js";
import { coverageLabel } from "../../features/grove/pressAccess.js";
import { articleHref, articlesDrawingOn } from "../../features/grove/pressArticles.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";
import { formatUpdated, ledgerFor } from "../../features/grove/pressReleases.js";
import { PRESS_METHODS_PATH, PRESS_WHATS_NEW_PATH } from "../../features/grove/pressRoutes.js";
import { COLLECTION_ICONS } from "./pressCollectionIcons";

/** A section, rendered only when it has something to say. */
function Block({ title, children }) {
  if (!children) return null;
  return (
    <section className="cp-ab__block">
      <h3 className="cp-ab__h">{title}</h3>
      {children}
    </section>
  );
}

export default function PressCollectionAbout({ entry, flagship, onClose }) {
  const written = articlesDrawingOn(entry.id);
  const panelRef = useRef(null);
  const closeRef = useRef(null);

  // Escape closes, and focus lands inside the panel when it opens: it is a
  // sheet over the table, and a reader who tabs off the end of it should not
  // find themselves in the rows behind it.
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const frame = requestAnimationFrame(() => closeRef.current?.focus());
    return () => {
      document.removeEventListener("keydown", onKey);
      cancelAnimationFrame(frame);
    };
  }, [onClose]);

  if (!entry) return null;
  const launch = LAUNCH_COLLECTION.find((item) => item.id === entry.id) ?? {};
  const catalog = PRESS_CATALOG_BY_ID[entry.id] ?? entry;
  const facts = collectionCedarFacts(entry.id);
  const tables = collectionTables(entry.id);
  const book = flagship ? codebookFor(flagship.key) : null;
  const releases = ledgerFor(entry.id) ?? [];
  const latest = releases[0] ?? null;

  return (
    <div className="cp-ab" role="dialog" aria-label={`About ${entry.name}`} ref={panelRef}>
      <header className="cp-ab__head">
        <p className="cp-ab__cap">Collection profile</p>
        <h2 className="cp-ab__name">
          <span className="cp-ab__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
          {entry.name}
        </h2>
        <button type="button" className="cp-ab__close" onClick={onClose} ref={closeRef} aria-label="Close the collection profile">
          <span aria-hidden="true">&times;</span>
        </button>
      </header>

      <div className="cp-ab__body">
        {/* The header's facts, as fields. A reader checking a figure wants
            the release and the coverage before they want the prose. */}
        <dl className="cp-ab__facts">
          {launch.version ? (<div><dt>Release</dt><dd>{launch.version}</dd></div>) : null}
          {launch.updated ? (<div><dt>Updated</dt><dd>{formatUpdated(launch.updated)}</dd></div>) : null}
          {coverageLabel(catalog) ? (<div><dt>Coverage</dt><dd>{coverageLabel(catalog)}</dd></div>) : null}
          {launch.rowsLabel ? (<div><dt>Records</dt><dd>{launch.rowsLabel}</dd></div>) : null}
          {Number.isInteger(facts?.n_tables) ? (<div><dt>Tables</dt><dd>{facts.n_tables}</dd></div>) : null}
        </dl>

        <Block title="What is in this collection">
          {catalog?.blurb || book?.row ? (
            <>
              {catalog?.blurb ? <p>{catalog.blurb}</p> : null}
              {/* The unit of observation, in the codebook's own words: the
                  single most useful sentence for anyone about to cite a
                  count, and it was not on this surface anywhere. */}
              {book?.row ? (
                <p className="cp-ab__unit">
                  <b>One row is</b> {book.row}
                </p>
              ) : null}
            </>
          ) : null}
        </Block>

        {/* ONE SOURCE NOTE, THEN THE REST BEHIND A DISCLOSURE.
            Owner, 2026-09-20: "The collection profile drawer is useful, but
            it is too essay-like. Its first viewport should be: what this
            collection covers / release, years, record count / what a record
            means / one source-method note / Read full collection notes."

            It was seven expanded sections — how it is built, what is not in
            it, every field, every table, the release ledger, the writing —
            which is the reference document a reader wants ONCE, in front of
            a reader who is deciding whether to open a table. The first
            screen answers the deciding question; the reference is one click
            away and loses nothing. */}
        {launch.sources ? (
          <p className="cp-ab__sources cp-ab__lead"><b>Sources.</b> {launch.sources}</p>
        ) : null}

        {/* THE OTHER HALF OF THE LOOP.
            The article page names the collections a piece drew on and offers
            their data. Read the other way, this is what a subscriber holding
            the records wants next: what somebody already wrote from them.
            Same `draws`, no second list to maintain.

            It is NOT inside the folded notes with the rest of the reference
            material, though the 2026-09-20 review put everything else there:
            a list of two links is navigation rather than an essay, and the
            table's "+N more" control opens this panel expecting to land on
            it. A button that promises one more piece and delivers a closed
            drawer is a broken promise. */}
        {written.length ? (
          <Block title="Research built from this collection">
            <ul className="cp-ab__reads">
              {written.map((article) => {
                const away = !article.hosted;
                const inner = (
                  <>
                    <span className="cp-ab__readtitle">{article.title}</span>
                    <span className="cp-ab__readmeta">
                      {article.date}
                      {away ? " · Tribal Business News" : ""}
                    </span>
                  </>
                );
                return (
                  <li key={article.id}>
                    {away ? (
                      <a className="cp-ab__read" href={articleHref(article)} target="_blank" rel="noreferrer">
                        {inner}
                      </a>
                    ) : (
                      <Link className="cp-ab__read" to={articleHref(article)}>
                        {inner}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          </Block>
        ) : null}

        <details className="cp-ab__more">
          <summary>Read the full collection notes</summary>
          <div className="cp-ab__morein">
        <Block title="How it is built">
          {launch.method || launch.sources || catalog?.linkage ? (
            <>
              {launch.method ? <p>{launch.method}</p> : null}
              {catalog?.linkage ? (
                <p className="cp-ab__sources"><b>How a record reaches its entity.</b> {catalog.linkage}</p>
              ) : null}
            </>
          ) : null}
        </Block>

        {/* WHAT IS NOT IN IT. Its own section, not a caveat in a paragraph:
            the brief asks for it and it is the section a reader who is about
            to publish needs most. The preview limit is true of every
            collection and is stated here rather than inferred from the
            badge over the table. */}
        <Block title="What is not in it">
          <>
            <p>
              This viewer reads the published preview: up to ten sample rows per table. A search
              that returns nothing may mean the collection holds nothing, or that the sampled rows
              did not include it. The release is the whole table.
            </p>
            {catalog?.limits ? <p>{catalog.limits}</p> : null}
          </>
        </Block>

        <Block title="Fields and definitions">
          {book?.fields?.length ? (
            <details className="cp-ab__fields">
              <summary>{book.fields.length} fields in {flagship?.label ?? "the flagship table"}</summary>
              <dl>
                {book.fields.map((field) => (
                  <div key={field.column}>
                    <dt>{field.label}</dt>
                    <dd>
                      {field.meaning}
                      <code>{field.column}</code>
                    </dd>
                  </div>
                ))}
              </dl>
            </details>
          ) : null}
        </Block>

        <Block title="Tables in this release">
          {tables.length ? (
            <ul className="cp-ab__tables">
              {tables.map((table) => (
                <li key={table.table ?? table.key}>{table.table ?? table.key}</li>
              ))}
            </ul>
          ) : null}
        </Block>

        <Block title="Changes in this release">
          {latest ? (
            <>
              <p className="cp-ab__rel">
                <b>{latest.version}</b>
                {latest.date ? ` · ${formatUpdated(latest.date)}` : ""}
              </p>
              {latest.note ? <p>{latest.note}</p> : null}
              <Link className="cp-ab__link" to={`${PRESS_WHATS_NEW_PATH}#${entry.id}-${String(latest.version).replace(/\./g, "-")}`}>
                This release in the change ledger <span aria-hidden="true">&#8594;</span>
              </Link>
            </>
          ) : null}
        </Block>

          </div>
        </details>

        <p className="cp-ab__foot">
          <Link className="cp-ab__link" to={PRESS_METHODS_PATH}>
            How Cedar Press builds its collections <span aria-hidden="true">&#8594;</span>
          </Link>
        </p>
      </div>
    </div>
  );
}
