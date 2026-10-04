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
// `collection.js`), the catalog, the codebook, and the release ledger. The
// one block that is not the release's is "Questions this collection can help
// answer", and it is not written here either: it is `COLLECTION_JOBS` in
// `pressJobs.js`, where every question names the codebook fields that answer
// it and the node suite checks those fields exist. A
// profile that paraphrased its collection would drift from it the first time
// a release moved, and the whole point of the page is to be the thing a
// reader checks a figure against.
import { useEffect, useRef } from "react";
import { Link } from "react-router";

import {
  LAUNCH_COLLECTION,
} from "../../features/grove/collection.js";
import { codebookFor } from "../../features/grove/explore.js";
import { coverageLabel } from "../../features/grove/pressAccess.js";
import { sampleRecordCount } from "../../features/grove/readerPresentation.js";
import { articleHref, articlesDrawingOn } from "../../features/grove/pressArticles.js";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog.js";
import { collectionQuestions } from "../../features/grove/pressJobs.js";
import { MAINTENANCE, NEED_ENRICHMENTS } from "../../features/grove/pressMethod.js";
import { formatUpdated, ledgerFor } from "../../features/grove/pressReleases.js";
import { PRESS_METHODS_PATH, PRESS_WHATS_NEW_PATH } from "../../features/grove/pressRoutes.js";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { focusWasWithin, keepTabInside, rememberFocus } from "../../features/grove/focusReturn.js";

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

export default function PressCollectionAbout({ entry, flagship, onClose, articles = [] }) {
  const written = articlesDrawingOn(entry?.id, articles);
  const panelRef = useRef(null);
  const closeRef = useRef(null);

  // Escape closes, and focus lands inside the panel when it opens: it is a
  // sheet over the table, and a reader who tabs off the end of it should not
  // find themselves in the rows behind it.
  //
  // That last clause was the intent and not the behaviour until 2026-10-04:
  // Tab ran off the end of the sheet into the rail and the rows, and closing
  // left focus on <body>. Tab now wraps inside the sheet, and closing returns
  // focus to the control that opened it (`focusReturn.js`).
  const restoreRef = useRef(null);
  useEffect(() => {
    restoreRef.current = rememberFocus();
    const panel = panelRef.current;
    return () => {
      if (focusWasWithin(panel)) restoreRef.current?.();
    };
  }, []);
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
      else keepTabInside(event, panelRef.current);
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
  const book = flagship ? codebookFor(flagship.key) : null;
  const releases = ledgerFor(entry.id) ?? [];
  const latest = releases.at(-1) ?? null;
  const questions = collectionQuestions(entry.id);
  const sampleRows = sampleRecordCount(flagship?.sampleRows);

  return (
    <div className="cp-ab" role="dialog" aria-modal="true" aria-label={`About ${entry.name}`} ref={panelRef}>
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
          {launch.updated ? (<div><dt>Preview updated</dt><dd>{formatUpdated(launch.updated)}</dd></div>) : null}
          {coverageLabel(catalog) ? (<div><dt>Coverage</dt><dd>{coverageLabel(catalog)}</dd></div>) : null}
          {sampleRows !== null ? (<div><dt>Sample records</dt><dd>{sampleRows.toLocaleString("en-US")}</dd></div>) : null}
          <div><dt>Maintained</dt><dd>{MAINTENANCE.label}</dd></div>
        </dl>

        <Block title="What is in this collection">
          {catalog?.blurb || book?.row ? (
            <>
              {catalog?.blurb ? <p>{catalog.blurb}</p> : null}
              {/* Cedar NEED's enrichments, said in full where the collection
                  profile says what the collection holds. */}
              {entry.id === "need" ? (
                <p data-testid="need-enrichments">
                  {NEED_ENRICHMENTS.patents} {NEED_ENRICHMENTS.ratings} {NEED_ENRICHMENTS.attachment}
                </p>
              ) : null}
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

        {/* Immediately after what it holds, so a reader deciding whether
            this is the collection for their question sees the questions it
            answers before the method behind them (owner, 2026-09-26). */}
        <Block title="Questions this collection can help answer">
          {questions.length ? (
            <ul className="cp-ab__qs">
              {questions.map((item) => (
                <li key={item.q}>{item.q}</li>
              ))}
            </ul>
          ) : null}
        </Block>

        {launch.sources ? (
          <p className="cp-ab__sources cp-ab__lead"><b>Sources.</b> {launch.sources}</p>
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
              This viewer reads the published preview: up to ten sample observations per record type. A search
              that returns nothing may mean the collection holds nothing, or that the sampled rows
              did not include it. The downloadable dataset contains the permitted observations.
            </p>
            {catalog?.limits ? <p>{catalog.limits}</p> : null}
          </>
        </Block>

        <Block title="Fields and definitions">
          {book?.fields?.length ? (
            <details className="cp-ab__fields">
              <summary>{book.fields.length} fields in {flagship?.label ?? "the dataset"}</summary>
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


        <Block title="Latest update">
          {latest ? (
            <>
              <p className="cp-ab__rel">
                <b>Updated</b>
                {latest.date ? ` · ${formatUpdated(latest.date)}` : ""}
              </p>
              {latest.note ? <p>{latest.note}</p> : null}
              <Link className="cp-ab__link" to={`${PRESS_WHATS_NEW_PATH}#${entry.id}-${String(latest.version).replace(/\./g, "-")}`}>
                See what changed <span aria-hidden="true">&#8594;</span>
              </Link>
            </>
          ) : null}
        </Block>
          </div>
        </details>

        {/* THE OTHER HALF OF THE LOOP.
            The article page names the collections a piece drew on and offers
            their data. Read the other way, this is what a subscriber holding
            the records wants next: what somebody already wrote from them.
            Same `draws`, no second list to maintain. */}
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

        <p className="cp-ab__foot">
          <Link className="cp-ab__link" to={PRESS_METHODS_PATH}>
            How Cedar Press builds its collections <span aria-hidden="true">&#8594;</span>
          </Link>
        </p>
      </div>
    </div>
  );
}
