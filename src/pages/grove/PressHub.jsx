// The front page's index of the service.
//
// This was a grid of icon tiles with a ? on each — a phone launcher, which
// is the wrong register for an intelligence product, and it made the reader
// poke at a question mark to learn what a section was. It is a directory
// now: every section states its name, what it holds and where it currently
// stands, so the front page reports rather than decorates. The counts are
// read from the catalog rather than written here, so the index cannot claim
// a section holds something it does not.
import { Link } from "react-router";

import { PRESS_ARTICLES } from "../../features/grove/pressArticles";
import { PRESS_CATALOG, PRESS_HISTORY_FROM } from "../../features/grove/pressCatalog";
import { formatUpdated, recentlyUpdated } from "../../features/grove/pressReleases";
import {
  PRESS_ARTICLES_PATH,
  PRESS_DATA_PATH,
  PRESS_METHODS_PATH,
  PRESS_WHATS_NEW_PATH,
} from "../../features/grove/pressRoutes";

/** What sits on a Cedar Press shelf: the Grove-only collections are not it. */
function pressCollections() {
  return PRESS_CATALOG.filter((entry) => entry.shelf !== "grove");
}

function sections() {
  const collections = pressCollections();
  const earliest = collections
    .map((entry) => entry.standardFrom ?? entry.historyFrom)
    .filter(Boolean);
  const newest = recentlyUpdated(1)[0];
  return [
    {
      id: "articles",
      label: "Articles",
      to: PRESS_ARTICLES_PATH,
      what: "Original research built from the collections, written for people who work in Indian Country's economy.",
      meta: `${PRESS_ARTICLES.length} briefs · newest ${PRESS_ARTICLES[0].date}`,
    },
    {
      id: "data",
      label: "Data",
      to: PRESS_DATA_PATH,
      what: "The collections themselves: coverage, method and the release, downloadable with your subscription.",
      meta: `${collections.length} collections · records from ${
        earliest.length ? Math.min(...earliest) : PRESS_HISTORY_FROM
      }`,
    },
    {
      id: "whats-new",
      label: "What’s new",
      to: PRESS_WHATS_NEW_PATH,
      what: "Every release, dated and versioned, so a figure you downloaded or cited can be traced to what changed.",
      meta: newest ? `Last release ${formatUpdated(newest.updated)}` : "Release history",
    },
    {
      id: "methods",
      label: "Methods",
      to: PRESS_METHODS_PATH,
      what: "How collections are sourced, resolved to Native entities and kept current — the reference for citing a number.",
      meta: "Sources · entity resolution · release policy",
    },
    {
      id: "access",
      label: "Plans and access",
      to: `${PRESS_DATA_PATH}#grove`,
      what: "What your subscription includes, what Cedar Press+ adds, and where Cedar Grove takes the same collections.",
      meta: "Cedar Press · Cedar Press+ · Cedar Grove",
    },
  ];
}

export default function PressHub() {
  return (
    <section className="cp-sec cp-idx" aria-label="Sections">
      <span className="cp-sec__band">Sections</span>
      <ul className="cp-idx__list">
        {sections().map((section) => (
          <li key={section.id}>
            <Link className="cp-idx__row" to={section.to}>
              <span className="cp-idx__id">
                <span className="cp-idx__name">{section.label}</span>
                <span className="cp-idx__what">{section.what}</span>
              </span>
              <span className="cp-idx__meta">{section.meta}</span>
              <span className="cp-idx__go" aria-hidden="true">&#8594;</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
