// The front page's section index.
//
// Six squares, sized like the collection tiles because those already proved
// the size on both pointers, and the same grid on desktop and phone so the
// two navigations stay symmetric. Each square carries what the section is
// and what it currently holds — counts read from the catalog rather than
// written here, so the index cannot claim a section holds something it does
// not — with a ? that states the section's purpose in the line under the
// grid, for a reader who wants more than the label before committing a tap.
import { useState } from "react";
import { Link } from "react-router";

import { PRESS_ARTICLES } from "../../features/grove/pressArticles";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { PRESS_CATALOG, PRESS_HISTORY_FROM } from "../../features/grove/pressCatalog";
import { formatUpdated, recentlyUpdated } from "../../features/grove/pressReleases";
import {
  PRESS_ARTICLES_PATH,
  PRESS_DATA_PATH,
  PRESS_METHODS_PATH,
  PRESS_WHATS_NEW_PATH,
} from "../../features/grove/pressRoutes";
import {
  ArticlesIcon,
  DataIcon,
  FeedbackIcon,
  MethodsIcon,
  WantMoreIcon,
  WhatsNewIcon,
} from "./pressHubIcons";

const CONTACT_HREF = "mailto:contact@lumecon.ai?subject=Cedar%20Press";

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
      icon: ArticlesIcon,
      meta: `${PRESS_ARTICLES.length} briefs`,
      what: "Original research built from the collections, written for people who work in Indian Country's economy.",
    },
    {
      id: "data",
      label: "Data",
      to: PRESS_DATA_PATH,
      icon: DataIcon,
      meta: `${collections.length} collections`,
      what: `Coverage, method and the release for every collection, ${
        earliest.length ? Math.min(...earliest) : PRESS_HISTORY_FROM
      } to present, downloadable with your subscription.`,
    },
    {
      id: "whats-new",
      label: "What’s new",
      to: PRESS_WHATS_NEW_PATH,
      icon: WhatsNewIcon,
      meta: newest ? formatUpdated(newest.updated) : "Releases",
      what: "Every release, dated and versioned, so a figure you downloaded or cited can be traced to what changed.",
    },
    {
      id: "methods",
      label: "Methods",
      to: PRESS_METHODS_PATH,
      icon: MethodsIcon,
      meta: "Reference",
      what: "How collections are sourced, resolved to Native entities and kept current — the reference for citing a number.",
    },
    {
      id: "access",
      label: "Plans and access",
      to: `${PRESS_DATA_PATH}#grove`,
      icon: WantMoreIcon,
      meta: "Subscription",
      what: "What your subscription includes, what Cedar Press+ adds, and where Cedar Grove takes the same collections.",
    },
    {
      id: "contact",
      label: "Contact",
      href: CONTACT_HREF,
      icon: FeedbackIcon,
      meta: "The research desk",
      what: "Corrections, data requests and what the collections should cover next, read by the team that builds them.",
    },
  ];
}

const IDLE_NOTE = "Select ? on a section for what it holds.";

export default function PressHub() {
  const [help, setHelp] = useState(null);
  const all = sections();
  const note = all.find((section) => section.id === help)?.what;
  return (
    <section className="cp-sec cp-hub" aria-label="Sections">
      <span className="cp-sec__band">Sections</span>
      <ul className="cp-hub__grid">
        {all.map((section) => {
          const inner = (
            <>
              <span className="cp-hub__mark" aria-hidden="true">{section.icon}</span>
              <span className="cp-hub__id">
                <span className="cp-hub__name">{section.label}</span>
                <span className="cp-hub__meta">{section.meta}</span>
              </span>
            </>
          );
          return (
            <li key={section.id}>
              {section.href ? (
                <a className="cp-hub__tile" href={section.href} onClick={() => track(EVENT.sectionOpened, { section: section.id })}>{inner}</a>
              ) : (
                <Link className="cp-hub__tile" to={section.to} onClick={() => track(EVENT.sectionOpened, { section: section.id })}>{inner}</Link>
              )}
              {/* Its own control beside the tile's link, never inside it: a
                  button inside an anchor is two answers to one tap. */}
              <button
                type="button"
                className="cp-hub__help"
                aria-label={`What ${section.label} holds`}
                aria-expanded={help === section.id}
                onClick={() => setHelp(section.id)}
                onMouseEnter={() => setHelp(section.id)}
                onFocus={() => setHelp(section.id)}
              >
                ?
              </button>
            </li>
          );
        })}
      </ul>
      {/* aria-live, so a screen reader hears the answer the ? paints. */}
      <p className="cp-hub__note" aria-live="polite">{note || IDLE_NOTE}</p>
    </section>
  );
}
