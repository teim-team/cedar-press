// REVIEW OWNER: Havala
//
// One feed, every collection, newest first.
//
// The reader closes on "the records change, Cedar changes with them", and
// this is where that claim is checkable. Deliberately one chronological list
// rather than a changelog per collection: a subscriber wants to know what moved
// since they last looked, not to audit ten separate histories.
//
// Three things keep it from being an endless page. Filters, because "what
// changed in Advocacy" is the question people actually arrive with — sticky,
// because the feed will eventually hold hundreds of releases. A search box,
// for the reader who remembers "an ownership correction involving
// contracting" but not when it landed. And a page-at-a-time reveal, because a
// feed that dumps every release it has ever had is a wall nobody scrolls to
// the bottom of.
//
// THIS PAGE IS THE PROVENANCE LAYER
// Every release keeps a stable anchor (#funding-v4-2) so a methodology change
// can be cited, and the change notes stay specific — "resolved four
// registrants to the tribes that retained them" is checkable, "improved our
// data" is not.

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";

// The Press routes code-split separately, so a direct visit or refresh loads
// this module first; without the stylesheet stack the page and its Cedar
// launcher render unstyled.

import { PRESS_CATALOG } from "../../features/grove/pressCatalog";
import {
  PRESS_RELEASES,
  RELEASE_FEED,
  RELEASE_KIND,
  formatUpdated,
  recentActivity,
} from "../../features/grove/pressReleases";
import { PRESS_DATA_PATH } from "../../features/grove/pressRoutes";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { AD_SLOT } from "../../features/grove/pressAds";
import PressAd from "./PressAd";
import { PressFoot, PressMast } from "./PressChrome";
import { PressCedarFab } from "./PressCedarFab";

/** One screen's worth. More arrives a page at a time, on request. */
const PAGE = 8;

/** Whether the address names a release in the feed. */
const linkedAnchor = (hash) => Boolean(hash) && RELEASE_FEED.some((entry) => entry.anchor === hash);

/**
 * Scroll a release into view, clear of the sticky filter bar.
 *
 * `scrollIntoView` lands the entry at the top of the window, where the
 * sticky filter then covers its heading; the overview's "recently updated"
 * links arrive here by permalink, so the landing has to show the release
 * they named. The bar's height is measured rather than assumed, because the
 * collection chips wrap to a second row on narrower screens.
 */
function landOn(hash) {
  const target = document.getElementById(hash);
  if (!target) return;
  target.scrollIntoView();
  const bar = document.querySelector(".cp-filter--stick");
  if (bar) window.scrollBy(0, -(bar.getBoundingClientRect().height + 16));
}

export default function CedarPressWhatsNew() {
  // The masthead carries the reader's profile and Sign out. These two pages
  // rendered `<PressMast section="..." />` with NO `user` and no
  // `onSignOut`, so a signed-in reader who navigated here lost the avatar
  // and the way out - the session was intact, the chrome just stopped
  // saying so. Articles and Data always passed both; these did not.
  const { user, logout } = useAuth();
  const entitled = canReadCedarPress(user);

  useDocumentTitle("What’s new");
  useScrollToTop();
  // Sitewide arrival language; the sticky filter stays out of it, since a
  // transform mid-arrival would fight its pinning.
  const fadeRoot = useFadeIn();
  // The feed is static data, flattened, sorted and indexed once at module
  // load (pressReleases.js); this page filters it and derives nothing.
  const all = RELEASE_FEED;
  const [collection, setCollection] = useState("all");
  const [kind, setKind] = useState("all");
  const [query, setQuery] = useState("");
  // A permalink arrival (#funding-v4-2) must find its release even when the
  // page-at-a-time reveal would have kept it below the fold, so the reveal
  // starts fully open when the address names a release.
  const [shown, setShown] = useState(() => {
    const hash = typeof window === "undefined" ? "" : window.location.hash.slice(1);
    return linkedAnchor(hash) ? Number.POSITIVE_INFINITY : PAGE;
  });

  const entries = useMemo(() => {
    const asked = query.trim().toLowerCase();
    return all.filter((entry) => {
      if (collection !== "all" && entry.id !== collection) return false;
      if (kind !== "all" && entry.kind !== kind) return false;
      return !asked || entry.haystack.includes(asked);
    });
  }, [all, collection, kind, query]);

  // Changing a filter resets the reveal: leaving it at twenty after narrowing
  // to one collection would show the whole filtered list at once and make the
  // control look like it did nothing.
  const choose = (setter) => (value) => {
    setter(value);
    setShown(PAGE);
  };

  // Land on the linked release once it has rendered; the router's own
  // scroll-to-top has already run by then. The hashchange listener covers a
  // permalink pasted while already on the page, where only the fragment
  // changes and the initializer above never re-runs.
  useEffect(() => {
    const land = () => {
      const hash = window.location.hash.slice(1);
      if (!linkedAnchor(hash)) return;
      setShown(Number.POSITIVE_INFINITY);
      requestAnimationFrame(() => landOn(hash));
    };
    const hash = window.location.hash.slice(1);
    if (hash) requestAnimationFrame(() => landOn(hash));
    window.addEventListener("hashchange", land);
    return () => window.removeEventListener("hashchange", land);
  }, [all]);

  // Only collections that actually have releases, so the filter never offers
  // a choice that returns nothing.
  const options = PRESS_CATALOG.filter((entry) => PRESS_RELEASES[entry.id]);
  // The trailing month, computed from the log itself: the maintenance is the
  // product, and these four lines are it made tangible.
  const activity = useMemo(() => recentActivity(30), []);
  const filtered = collection !== "all" || kind !== "all" || query.trim() !== "";
  const visible = entries.slice(0, shown);
  const rest = entries.length - visible.length;

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="whats-new" />

        {/* Title across the page rather than down a 62ch column: this is the
            widest thing on the page and it was using half of it. The standing
            explanation sits under it, and the activity summary holds the
            second column — the newest release is already the first row of the
            feed, so repeating it here said nothing. */}
        <section className="cp-nh cp-fade">
          <p className="cp-hero__access">Collection updates</p>
          <h1 className="cp-nh__title">Everything that changed, newest first.</h1>
          {/* ONE LINE, NOT TWO PARAGRAPHS.
              The ledger below is the page, and this was 60 words of preamble
              above it saying what a changelog is. What survives is the part a
              reader cannot infer from the rows: that methodology releases can
              move figures somebody has already published, and that old
              versions stay addressable. */}
          <p className="cp-nh__sub">
            Methodology releases are marked, because they can move figures somebody has already
            published. Every version keeps its address, so a citation can name the release it
            came from.
          </p>
          <dl className="cp-nh__pulse">
            <dt>Last {activity.days} days</dt>
            <dd className="cp-nh__pulselead">
              {activity.releases} {activity.releases === 1 ? "release" : "releases"}
            </dd>
            {activity.releases ? (
              <>
                <dd>
                  {activity.collections}{" "}
                  {activity.collections === 1 ? "collection" : "collections"} updated
                </dd>
                <dd>
                  {activity.methodology} methodology{" "}
                  {activity.methodology === 1 ? "release" : "releases"}
                </dd>
              </>
            ) : null}
            {activity.latest ? <dd>Latest: {formatUpdated(activity.latest)}</dd> : null}
          </dl>
        </section>

        {/* Sticky: the feed will eventually hold hundreds of releases, and
            the way through them should not scroll away with the hero. */}
        <div className="cp-filter cp-filter--stick">
          <div className="cp-filter__set cp-filter__set--scroll" role="group" aria-label="Filter by collection">
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
          <input
            className="cp-filter__search"
            type="search"
            value={query}
            onChange={(event) => choose(setQuery)(event.target.value)}
            placeholder="Search releases…"
            aria-label="Search releases"
          />
          <p className="cp-filter__count" aria-live="polite">
            {entries.length} {entries.length === 1 ? "release" : "releases"}
            {filtered ? " matching" : ""}
          </p>
        </div>

        {visible.length ? (
          <ol className="cp-feed cp-fade">
            {visible.map((entry, i) => {
              const { name, anchor } = entry;
              const method = entry.kind === RELEASE_KIND.METHOD;
              // TWELVE COLLECTIONS SHIP ON ONE DAY, AND THE DATE SAID SO
              // TWELVE TIMES. The feed is newest-first and a release day
              // moves every collection at once, so the left column was the
              // same date repeated down the page — which reads as a column of
              // filler rather than as one day's work. A date that repeats the
              // one above it is a run, not a new fact, so only the first
              // entry of a run carries it. The date is still on every item
              // for a screen reader and for anyone landing on a permalink,
              // as the datetime the element announces.
              const runStart = i === 0 || visible[i - 1].date !== entry.date;
              return (
                <li className="cp-feed__item" id={anchor} key={anchor}>
                  <time
                    className={`cp-feed__when${runStart ? "" : " cp-feed__when--same"}`}
                    dateTime={entry.date}
                  >
                    {runStart ? formatUpdated(entry.date) : <span className="sr-only">{formatUpdated(entry.date)}</span>}
                  </time>
                  <div className="cp-feed__what">
                    {/* The kind on every entry, not only in the filter: a
                        methodology release read cold must announce itself. */}
                    {/* One line, not three. The kind, the collection and the
                        version were stacked, so a release with a one-line
                        note took 120px and a day that moved twelve
                        collections was a page and a half of mostly air. They
                        are one row now; the note and the change list keep
                        their own lines because those are what a reader came
                        for. */}
                    <h2 className="cp-feed__name">
                      <span className={`cp-feed__kind${method ? " cp-feed__kind--method" : ""}`}>
                        {method ? "Methodology" : "Data update"}
                      </span>
                      <span>{name}</span>
                      {/* The version is the release's permalink: a citation
                          names one, and #funding-v4-2 gives the name a stable
                          address to point at. */}
                      <a className="cp-feed__ver" href={`#${anchor}`} title="Link to this release">
                        {entry.version}
                      </a>
                    </h2>
                    {entry.note ? <p className="cp-feed__note">{entry.note}</p> : null}
                    {/* WHAT CHANGED, THEN THE ARITHMETIC.
                        Every release lists its table and row counts beside
                        whatever actually changed, at the same weight, so a
                        methodology correction and "14 tables, 3,646,750 rows"
                        read as two equal facts. The counts are release
                        metadata — true, worth keeping, and not the news. */}
                    {(() => {
                      const routine = (line) => /^Release:\s/.test(line);
                      const news = entry.changed.filter((l) => !routine(l));
                      const counts = entry.changed.filter(routine);
                      // The exact change list is a disclosure now. A release
                      // day moves twelve collections and each one listed its
                      // changes in full, so the ledger became a wall and the
                      // dates it is ordered by were pages apart. The note
                      // above stays visible as the summary; this is the
                      // detail a reader opens when a particular release is
                      // the one they care about.
                      if (!news.length && !counts.length) return null;
                      return (
                        <details className="cp-feed__detail">
                          <summary>
                            What changed{news.length ? ` · ${news.length} ${news.length === 1 ? "note" : "notes"}` : ""}
                          </summary>
                          {news.length ? (
                            <ul className="cp-feed__list">
                              {news.map((line) => <li key={line}>{line}</li>)}
                            </ul>
                          ) : null}
                          {counts.length ? (
                            <p className="cp-feed__counts">
                              {counts.map((line) => line.replace(/^Release:\s/, "")).join(" · ")}
                            </p>
                          ) : null}
                        </details>
                      );
                    })()}
                    <p className="cp-feed__acts">
                      {/* A retired collection's release is history a reader
                          can still cite; there is no shelf to walk to. */}
                      {entry.retired ? (
                        <span className="cp-feed__act cp-feed__act--still">
                          No longer on the shelf; kept for citation
                        </span>
                      ) : (
                        /* THIS collection, not the collections page.
                           It linked to /data flat, so a reader who came to
                           see what changed in NAGPRA landed on Federal
                           Funding and had to find NAGPRA again. The page
                           opens on whichever collection a link names. */
                        <Link className="cp-feed__act" to={`${PRESS_DATA_PATH}?c=${entry.id}`}>
                          View collection <span aria-hidden="true">&#8594;</span>
                        </Link>
                      )}
                      {/* Cedar, scoped to the collection with the question
                          already phrased: the release log behind this feed is
                          exactly what the profile layer answers from. */}
                      <button
                        type="button"
                        className="cp-feed__act"
                        onClick={() =>
                          window.dispatchEvent(
                            new CustomEvent("cedar:ask-collection", {
                              detail: {
                                id: entry.id,
                                name,
                                q: `What changed in ${name} ${entry.version}?`,
                              },
                            }),
                          )
                        }
                      >
                        Ask Cedar about this update <span aria-hidden="true">&#8594;</span>
                      </button>
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="cp-feed__none">No releases match that combination yet.</p>
        )}

        {/* The list and the control that continues it are one thing, so
            nothing goes between them. The slot used to sit here, above "Show
            8 more", which put an advertisement inside the feed's own
            pagination — the reader reached the end of the releases, met an ad,
            and then found the button that was supposed to follow the list. */}
        {rest > 0 ? (
          <p className="cp-feed__more">
            <button type="button" className="cp-band__allbtn" onClick={() => setShown((n) => n + PAGE)}>
              Show {Math.min(rest, PAGE)} more <span aria-hidden="true">&#8595;</span>
            </button>
            <span className="cp-feed__left">{rest} older</span>
          </p>
        ) : null}

        {/* Sponsorship rule 5: never in a filtered view. The slot rides the
            full feed only, and never an empty result. It sits after the feed
            and its control, which is where a page pauses. */}
        {filtered ? null : <PressAd slot={AD_SLOT.FEED} />}

        <PressFoot />
        <PressCedarFab />
      </main>
    </div>
  );
}
