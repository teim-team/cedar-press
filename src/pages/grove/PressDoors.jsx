// REVIEW OWNER: Havala
//
// The rest of the service, as a ledger under the collections: four rows,
// each what a section is and what it holds right now, with one way in.
//
// This replaced six identical icon squares. A square carries a label and a
// count; a row carries the newest brief's title, the three collections that
// moved most recently, and the priorities subscribers are putting points
// toward, which is the difference between a map of the service and the
// service. Counts and titles are read from the catalog, the release record
// and the priorities, never typed here.

import { Link } from "react-router";

import { PRESS_ARTICLES } from "../../features/grove/pressArticles";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog";
import { pointsWord, published, sortPriorities } from "../../features/grove/pressPriorities.js";
import { anchorOf, formatUpdated, latestRelease, recentlyUpdated } from "../../features/grove/pressReleases";
import {
  PRESS_ARTICLES_PATH,
  PRESS_METHODS_PATH,
  PRESS_PRIORITIES_PATH,
  PRESS_WHATS_NEW_PATH,
  pressArticlePath,
} from "../../features/grove/pressRoutes";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { usePriorities } from "../../features/grove/usePriorities.js";

function Door({ id, label, title, children, to, href, action }) {
  const onClick = () => track(EVENT.sectionOpened, { section: id });
  return (
    <li className="cp-door" data-testid="door" data-door={id}>
      <span className="cp-door__label">{label}</span>
      <div className="cp-door__body">
        <h3 className="cp-door__title">{title}</h3>
        {children}
        {to ? (
          <Link className="cp-door__act" to={to} onClick={onClick}>
            {action} <span aria-hidden="true">&#8594;</span>
          </Link>
        ) : (
          <a className="cp-door__act" href={href} target="_blank" rel="noreferrer" onClick={onClick}>
            {action} <span aria-hidden="true">&#8594;</span>
          </a>
        )}
      </div>
    </li>
  );
}

export default function PressDoors({ signedIn }) {
  // Newest hosted brief: the strip is newest-first, and an external piece
  // opens on TBN, which is not "read it here".
  const latestBrief = PRESS_ARTICLES.find((article) => article.hosted) ?? null;
  const recent = recentlyUpdated(3);
  const { priorities, status } = usePriorities({ signedIn });
  const top = sortPriorities(priorities).slice(0, 3);
  const shipped = published(priorities)[0] ?? null;

  return (
    <section className="cp-doors cp-fade" aria-label="Sections">
      <span className="cp-sec__band">Also in Cedar Press</span>
      <ol className="cp-doors__list">
        <Door
          id="articles"
          label="Research briefs"
          title={latestBrief ? latestBrief.title : "Original research built from the collections"}
          to={latestBrief ? pressArticlePath(latestBrief.id) : PRESS_ARTICLES_PATH}
          action={latestBrief ? "Read the latest brief" : "Read the briefs"}
        >
          <p>
            {PRESS_ARTICLES.length} briefs, written from the collections for people who work in
            Indian Country&rsquo;s economy. <Link to={PRESS_ARTICLES_PATH}>All briefs</Link>.
          </p>
        </Door>

        <Door
          id="whats-new"
          label="What’s new"
          title="Every release, dated and versioned."
          to={PRESS_WHATS_NEW_PATH}
          action="See every release"
        >
          <p>A figure you downloaded or cited can be traced to what changed. Most recently:</p>
          <ul className="cp-door__list">
            {recent.map((release) => {
              const latest = latestRelease(release.id);
              const to = latest
                ? `${PRESS_WHATS_NEW_PATH}#${anchorOf({ id: release.id, version: latest.version })}`
                : PRESS_WHATS_NEW_PATH;
              return (
                <li key={release.id}>
                  <Link to={to}>{PRESS_CATALOG_BY_ID[release.id]?.name ?? release.id}</Link>
                  <span className="cp-door__date">{formatUpdated(release.updated)}</span>
                </li>
              );
            })}
          </ul>
        </Door>

        <Door
          id="methods"
          label="Methods"
          title="How a collection is built, and how it is kept current."
          to={PRESS_METHODS_PATH}
          action="Read the methods"
        >
          <p>
            How records are sourced, resolved to Native entities and maintained: the reference to
            open before citing a number.
          </p>
        </Door>

        <Door
          id="priorities"
          label="Priorities"
          title="What Cedar researches next is decided by subscribers."
          to={PRESS_PRIORITIES_PATH}
          action="Shape the research"
        >
          <ol className="cp-door__list cp-door__list--ranked">
            {top.map((p) => (
              <li key={p.id}>
                <span>{p.title}</span>
                <span className="cp-door__date">{status === "ok" ? pointsWord(p.points) : "not yet counted"}</span>
              </li>
            ))}
          </ol>
          {shipped ? (
            <p>
              <b>{shipped.title}</b> was one of subscribers&rsquo; highest priorities and has been
              published.
              {shipped.published_output ? <> <a href={shipped.published_output}>See what was published</a>.</> : null}
            </p>
          ) : null}
        </Door>
      </ol>
    </section>
  );
}
