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
// changed in Lobbying" is the question people actually arrive with — sticky,
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

// The Press routes code-split separately, so a direct visit or refresh loads
// this module first; without the stylesheet stack the page and its Cedar
// launcher render unstyled.
import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";

import { PRESS_CATALOG, PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog";
import {
  PRESS_RELEASES,
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

/** Every release from every collection, flattened and sorted by date. */
function buildFeed() {
  return Object.entries(PRESS_RELEASES)
    .flatMap(([id, release]) => release.history.map((entry) => ({ id, ...entry })))
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}

/** The release's stable anchor: cite `#funding-v4-2` and it stays citable. */
function anchorOf(entry) {
  return `${entry.id}-${entry.version.replace(/\./g, "-")}`;
}

export default function CedarPressWhatsNew() {
  useDocumentTitle("What’s new");
  useScrollToTop();
  // Sitewide arrival language; the sticky filter stays out of it, since a
  // transform mid-arrival would fight its pinning.
  const fadeRoot = useFadeIn();
  const all = useMemo(() => buildFeed(), []);
  const [collection, setCollection] = useState("all");
  const [kind, setKind] = useState("all");
  const [query, setQuery] = useState("");
  // A permalink arrival (#funding-v4-2) must find its release even when the
  // page-at-a-time reveal would have kept it below the fold, so the reveal
  // starts fully open when the address names a release.
  const [shown, setShown] = useState(() => {
    const hash = typeof window === "undefined" ? "" : window.location.hash.slice(1);
    const linked = hash && buildFeed().some((entry) => anchorOf(entry) === hash);
    return linked ? Number.POSITIVE_INFINITY : PAGE;
  });

  const entries = useMemo(() => {
    const asked = query.trim().toLowerCase();
    return all.filter((entry) => {
      if (collection !== "all" && entry.id !== collection) return false;
      if (kind !== "all" && entry.kind !== kind) return false;
      if (!asked) return true;
      const name = PRESS_CATALOG_BY_ID[entry.id]?.name ?? entry.id;
      return [name, entry.version, entry.note ?? "", ...entry.changed]
        .join(" ")
        .toLowerCase()
        .includes(asked);
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
      if (!hash || !all.some((entry) => anchorOf(entry) === hash)) return;
      setShown(Number.POSITIVE_INFINITY);
      requestAnimationFrame(() => document.getElementById(hash)?.scrollIntoView());
    };
    const hash = window.location.hash.slice(1);
    if (hash) requestAnimationFrame(() => document.getElementById(hash)?.scrollIntoView());
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
        <PressMast section="whats-new" />

        {/* Title across the page rather than down a 62ch column: this is the
            widest thing on the page and it was using half of it. The standing
            explanation sits under it, and the activity summary holds the
            second column — the newest release is already the first row of the
            feed, so repeating it here said nothing. */}
        <section className="cp-nh cp-fade">
          <p className="cp-hero__access">Collection updates</p>
          <h1 className="cp-nh__title">Everything that changed, newest first.</h1>
          <div>
            <p className="cp-nh__sub">
              Cedar collections are maintained as new records, ownership changes, corrections and
              historical evidence arrive. Methodology releases are marked, because they can affect
              figures somebody has already published.
            </p>
            {/* The principle this page exists for, said where it applies: the
                changelog is the provenance layer. */}
            <p className="cp-nh__why">
              Release history is preserved so a figure can be traced to the exact version of the
              collection it was published from.
            </p>
          </div>
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
            {visible.map((entry) => {
              const name = PRESS_CATALOG_BY_ID[entry.id]?.name ?? entry.id;
              const anchor = anchorOf(entry);
              const method = entry.kind === RELEASE_KIND.METHOD;
              return (
                <li className="cp-feed__item" id={anchor} key={anchor}>
                  <span className="cp-feed__when">{formatUpdated(entry.date)}</span>
                  <div className="cp-feed__what">
                    {/* The kind on every entry, not only in the filter: a
                        methodology release read cold must announce itself. */}
                    <span className={`cp-feed__kind${method ? " cp-feed__kind--method" : ""}`}>
                      {method ? "Methodology" : "Data update"}
                    </span>
                    <h2 className="cp-feed__name">
                      <span>{name}</span>
                      {/* The version is the release's permalink: a citation
                          names one, and #funding-v4-2 gives the name a stable
                          address to point at. */}
                      <a className="cp-feed__ver" href={`#${anchor}`} title="Link to this release">
                        {entry.version}
                      </a>
                    </h2>
                    {entry.note ? <p className="cp-feed__note">{entry.note}</p> : null}
                    <ul className="cp-feed__list">
                      {entry.changed.map((line) => <li key={line}>{line}</li>)}
                    </ul>
                    <p className="cp-feed__acts">
                      <Link className="cp-feed__act" to={PRESS_DATA_PATH}>
                        View collection <span aria-hidden="true">&#8594;</span>
                      </Link>
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

        {/* Sponsorship rule 5: never in a filtered view. The slot rides the
            full feed only, and never an empty result. */}
        {filtered ? null : <PressAd slot={AD_SLOT.FEED} />}

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
