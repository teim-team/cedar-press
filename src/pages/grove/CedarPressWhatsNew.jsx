// REVIEW OWNER: Havala
//
// One feed, every collection, newest first.
//
// The reader closes on "the records change, Cedar changes with them", and
// this is where that claim is checkable. Deliberately one chronological list
// rather than a changelog per collection: a subscriber wants to know what moved
// since they last looked, not to audit ten separate histories.
//
// Two things keep it from being an endless page. A filter, because "what
// changed in Lobbying" is the question people actually arrive with, and a
// page-at-a-time reveal, because a feed that dumps every release it has ever
// had is a wall nobody scrolls to the bottom of.

import { useMemo, useState } from "react";
import { Link } from "react-router";

// The Press routes code-split separately, so a direct visit or refresh loads
// this module first; without the stylesheet stack the page and its Cedar
// launcher render unstyled.
import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import { PRESS_CATALOG, PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog";
import {
  PRESS_RELEASES,
  RELEASE_KIND,
  formatUpdated,
} from "../../features/grove/pressReleases";
import {
  PRESS_METHODS_PATH,
  PRESS_PATH,
} from "../../features/grove/pressRoutes";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { AD_SLOT } from "../../features/grove/pressAds";
import PressAd from "./PressAd";
import { PressFoot, PressMast } from "./PressChrome";
import { PressCedarFab } from "./PressCedarFab";

/** One screen's worth. More arrives a page at a time, on request. */
const PAGE = 8;

/** Every release from every collection, flattened and sorted by date. */
function buildFeed() {
  return Object.entries(PRESS_RELEASES)
    .flatMap(([id, release]) => release.history.map((entry) => ({ id, ...entry })))
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}

export default function CedarPressWhatsNew() {
  useDocumentTitle("What\u2019s new");
  useScrollToTop();
  const all = useMemo(() => buildFeed(), []);
  const [collection, setCollection] = useState("all");
  const [kind, setKind] = useState("all");
  const [shown, setShown] = useState(PAGE);

  const entries = useMemo(
    () =>
      all.filter(
        (entry) =>
          (collection === "all" || entry.id === collection) &&
          (kind === "all" || entry.kind === kind),
      ),
    [all, collection, kind],
  );

  // Changing a filter resets the reveal: leaving it at twenty after narrowing
  // to one collection would show the whole filtered list at once and make the
  // control look like it did nothing.
  const choose = (setter) => (value) => {
    setter(value);
    setShown(PAGE);
  };

  // Only collections that actually have releases, so the filter never offers
  // a choice that returns nothing.
  const options = PRESS_CATALOG.filter((entry) => PRESS_RELEASES[entry.id]);
  const newest = all[0] ?? null;
  const visible = entries.slice(0, shown);
  const rest = entries.length - visible.length;

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page">
        <PressMast section="whats-new" />

        {/* Title across the page rather than down a 62ch column: this is the
            widest thing on the page and it was using half of it. The standing
            explanation and the newest release sit under it on one line, so the
            opening reaches both edges instead of trailing off. */}
        <section className="cp-nh">
          <p className="cp-hero__access">Collection updates</p>
          <h1 className="cp-nh__title">Everything that changed, newest first.</h1>
          <p className="cp-nh__sub">
            Cedar collections are maintained as new records, ownership changes, corrections and
            historical evidence arrive. Methodology releases are marked, because they can affect
            figures somebody has already published.
          </p>
          {newest ? (
            <p className="cp-nh__last">
              <span>Most recent</span>
              <b>{PRESS_CATALOG_BY_ID[newest.id]?.name ?? newest.id}</b>
              <span>{formatUpdated(newest.date)}</span>
            </p>
          ) : null}
        </section>

        <div className="cp-filter">
          <div className="cp-filter__set" role="group" aria-label="Filter by collection">
            <span className="cp-filter__cap">Collection</span>
            <button
              type="button"
              className={`cp-chip${collection === "all" ? " is-on" : ""}`}
              onClick={() => choose(setCollection)("all")}
            >
              All
            </button>
            {options.map((entry) => (
              <button
                type="button"
                key={entry.id}
                className={`cp-chip${collection === entry.id ? " is-on" : ""}`}
                onClick={() => choose(setCollection)(entry.id)}
              >
                {entry.short}
              </button>
            ))}
          </div>
          <div className="cp-filter__set" role="group" aria-label="Filter by release kind">
            <span className="cp-filter__cap">Kind</span>
            {[
              ["all", "All"],
              [RELEASE_KIND.DATA, "Data"],
              [RELEASE_KIND.METHOD, "Methodology"],
            ].map(([value, label]) => (
              <button
                type="button"
                key={value}
                className={`cp-chip${kind === value ? " is-on" : ""}`}
                onClick={() => choose(setKind)(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="cp-filter__count" aria-live="polite">
            {entries.length} {entries.length === 1 ? "release" : "releases"}
          </p>
        </div>

        {visible.length ? (
          <ol className="cp-feed">
            {visible.map((entry) => (
              <li className="cp-feed__item" key={`${entry.id}-${entry.version}`}>
                <span className="cp-feed__when">{formatUpdated(entry.date)}</span>
                <div className="cp-feed__what">
                  {/* The name is text: this feed is the one page that tracks
                      changes, so there is no per-collection page to send
                      anyone to. */}
                  <h2 className="cp-feed__name">
                    <span>{PRESS_CATALOG_BY_ID[entry.id]?.name ?? entry.id}</span>
                    {/* The version, because citations and downloads name one:
                        this feed is where a reader maps "v4.1" to what
                        changed, which it cannot do from a date alone. */}
                    <span className="cp-feed__ver">{entry.version}</span>
                    {entry.kind === RELEASE_KIND.METHOD ? (
                      <span className="cp-feed__tag">Methodology</span>
                    ) : null}
                  </h2>
                  {entry.note ? <p className="cp-feed__note">{entry.note}</p> : null}
                  <ul className="cp-feed__list">
                    {entry.changed.map((line) => <li key={line}>{line}</li>)}
                  </ul>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="cp-feed__none">No releases match that combination yet.</p>
        )}

        {/* Sponsorship rule 5: never in a filtered view. The slot rides the
            full feed only, and never an empty result. */}
        {collection === "all" && kind === "all" ? <PressAd slot={AD_SLOT.FEED} /> : null}

        {rest > 0 ? (
          <p className="cp-feed__more">
            <button type="button" className="cp-band__allbtn" onClick={() => setShown((n) => n + PAGE)}>
              Show {Math.min(rest, PAGE)} more <span aria-hidden="true">&#8595;</span>
            </button>
            <span className="cp-feed__left">{rest} older</span>
          </p>
        ) : null}

        <PressFoot />
        <PressCedarFab />
      </main>
    </div>
  );
}
