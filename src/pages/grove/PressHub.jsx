// The front page's section index.
//
// Six squares, sized like the collection tiles because those already proved
// the size on both pointers, and the same grid on desktop and phone so the
// two navigations stay symmetric. Each square carries what the section is
// and what it currently holds — counts read from the catalog rather than
// written here, so the index cannot claim a section holds something it does
// not. Pointing at a tile states the section's purpose in the line under
// the grid — the same point-to-read language as the shelves, with the same
// sticky selection — so a reader gets more than the label before
// committing a tap, without a second control on every tile.
import { useState } from "react";
import { Link } from "react-router";

import { PRESS_ARTICLES, TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { canOpenDataset, coverageFrom } from "../../features/grove/pressAccess";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { PRESS_CATALOG } from "../../features/grove/pressCatalog";
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

/** The collections THIS reader's plan opens: a Cedar Press subscriber has
 *  six, not the catalog's eleven, and a tile that counts the higher shelf
 *  describes a product they did not buy. */
function pressCollections(user) {
  return PRESS_CATALOG.filter(
    (entry) => entry.shelf !== "grove" && canOpenDataset(user, entry),
  );
}

function sections(user) {
  const collections = pressCollections(user);
  // The collections this reader opens, at the depth Cedar holds them: one
  // number per collection, the same for every plan that reaches it.
  const earliest = collections.map((entry) => coverageFrom(entry)).filter(Boolean);
  // What the plans tile can honestly offer this reader: Cedar Press+ is an
  // upgrade only to someone who does not already have it; above that, the
  // next rung is Cedar Grove.
  const hasPro = canOpenDataset(user, { shelf: "pro" });
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
      label: "Collections",
      to: PRESS_DATA_PATH,
      icon: DataIcon,
      meta: `${collections.length} collections`,
      // "reaching back as far as", never "<year> to present". The minimum is
      // one collection's floor — Legislation's 1973 — and eleven of the twelve
      // start later, two of them being rosters with no start at all. A
      // shelf-wide sentence cannot carry a per-collection fact, and the tiles
      // below give each collection its own.
      what: `Coverage, method and the release for every collection${
        earliest.length ? `, reaching back as far as ${Math.min(...earliest)},` : ","
      } downloadable with your subscription.`,
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
      // Upgrades are bought at Tribal Business News, so the tile goes to
      // the plans page rather than a section that only describes them.
      id: "access",
      label: "Plans and access",
      href: TBN_PLANS_URL,
      external: true,
      icon: WantMoreIcon,
      meta: "Subscription",
      what: hasPro
        ? "Your membership, managed through Tribal Business News. The step beyond this shelf is Cedar Grove, where the same collections open for analysis."
        : "What your subscription includes and what Cedar Press+ adds, managed and upgraded through Tribal Business News.",
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

const IDLE_NOTE = "Point at a section for what it holds.";

export default function PressHub({ user }) {
  const [help, setHelp] = useState(null);
  const all = sections(user);
  const note = all.find((section) => section.id === help)?.what;
  return (
    <section className="cp-sec cp-hub cp-fade" aria-label="Sections">
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
          // The selection is sticky, like the shelves: it changes when
          // another tile is pointed at, never back to the idle hint, so the
          // line below is readable at leisure.
          const watch = {
            onMouseEnter: () => setHelp(section.id),
            onFocus: () => setHelp(section.id),
            onClick: () => track(EVENT.sectionOpened, { section: section.id }),
          };
          return (
            <li key={section.id}>
              {section.href ? (
                <a
                  className="cp-hub__tile"
                  href={section.href}
                  {...(section.external ? { target: "_blank", rel: "noreferrer" } : {})}
                  {...watch}
                >
                  {inner}
                </a>
              ) : (
                <Link className="cp-hub__tile" to={section.to} {...watch}>{inner}</Link>
              )}
            </li>
          );
        })}
      </ul>
      {/* aria-live, so a screen reader hears the answer the pointer paints. */}
      <p className="cp-hub__note" aria-live="polite">{note || IDLE_NOTE}</p>
    </section>
  );
}
