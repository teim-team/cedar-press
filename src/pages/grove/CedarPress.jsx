// REVIEW OWNER: Havala
//
// Cedar Press: the reader.
//
// Behind an entitlement, not public. `canReadCedarPress` decides whether this
// renders the reader or hands off to PressGate, and the two never appear
// together: the gate is a full-bleed split screen with no masthead, because a
// sign-in that inherits the page chrome reads as a page with a form on it.
//
// THE PAGE HOLDS TWO KINDS OF THING
// Articles built from the collections, and the collections themselves. Most
// readers arrive wanting one of them, so the bar under the masthead is a
// filter rather than a row of jump links, and it is aggressive: Data is the
// shelves the reader can open and nothing else, Articles is the briefs and
// nothing else. Everything a filtered view drops (the hero, the traceability
// rule, the entity explainer, the locked shelf, the Cedar Grove pitch, the
// close) is argument rather than answer, and argument belongs to Everything.
//
// WHERE THIS MEETS CEDAR GROVE
// Grove is a different product, not a further rung, which is why the teaser
// sits below a rule and never appears in a filtered view. It shows a
// Grove-exclusive collection against what a Cedar Press reader still sees, so
// the boundary itself is the argument. See docs/cedar-press-architecture.md
// section 4 for what a Grove preview may and may not show.
//
// Built from the app's own tokens and the collection's own figure specs, so
// this page cannot drift from what subscribers see inside Grove.

// The app's stylesheet order, so the Cedar widget markup below is styled by
// exactly the rules that style it inside the product: index.css base,
// redesign.css retheme, then this page's own layout.
import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";

import { useAuth } from "../../context/useAuth";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { NATIVE_LINKAGE, PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog";
import { formatUpdated, recentlyUpdated } from "../../features/grove/pressReleases";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { LUMECON_URL, PRESS_ARTICLES, TBN_URL } from "../../features/grove/pressArticles";
import {
  PRESS_METHODS_PATH,
  PRESS_REQUEST_PATH,
  PRESS_RESEARCH_PATH,
  PRESS_WHATS_NEW_PATH,
  pressArticlePath,
} from "../../features/grove/pressRoutes";
import { AD_SLOT } from "../../features/grove/pressAds";
import { appUrl } from "../../features/grove/appLink.js";
import { Contours, Halo } from "./pressAtmosphere";
import PressAd from "./PressAd";
import { PressCedarFab } from "./PressCedarFab";
import PressGate from "./PressGate";
import PressShelf from "./PressShelf";

// The page holds two kinds of thing and a reader usually wants one of them.
// This is a filter rather than a row of jump links: picking Data leaves the
// collections on the page and takes the articles off it, so "I only want the
// data" is one click instead of a scroll past everything else.
const VIEWS = [
  { id: "all", label: "Everything" },
  { id: "data", label: "Data" },
  { id: "articles", label: "Articles" },
];


function ArticleCard({ article, compact = false }) {
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === article.datasetId);
  const className = compact ? "cp-art cp-art--compact" : "cp-art cp-art--lead";
  const inner = (
    <>
      {/* Sector photography stands in until the real brief publishes with
          its own image. */}
      <div className="cp-art__art">
        <img className="cp-art__img" src={article.image} alt={article.imageAlt} loading="lazy" />
      </div>
      <div className="cp-art__body">
        {/* A demonstration placeholder says so on the card: the body and its
            figures are invented, and "Original research" would be a claim the
            piece cannot carry until sourced work replaces it. */}
        <span className="cp-art__tag">
          {article.demonstration ? "Demonstration" : article.kind || "Original research"}
          <b>{dataset?.name || article.tag}</b>
        </span>
        <h3 className="cp-art__title">{article.title}</h3>
        <p className="cp-art__dek">{article.dek}</p>
        <span className="cp-art__meta">
          {article.date} · from {dataset?.name}
          {article.hosted ? null : " · on Tribal Business News"}
        </span>
      </div>
    </>
  );

  // A hosted piece opens here, beside its data and its rail. One that
  // publishes on Tribal Business News opens there, in a new tab, and the meta
  // line above says so before the click rather than after it.
  return article.hosted ? (
    <Link className={className} to={pressArticlePath(article.id)}>{inner}</Link>
  ) : (
    <a className={className} href={article.href} target="_blank" rel="noreferrer">
      {inner}
    </a>
  );
}

export default function CedarPress() {
  const { user, loading, logout } = useAuth();
  const { hash } = useLocation();
  const [view, setView] = useState("all");
  const showData = view !== "articles";
  const showArticles = view !== "data";
  // Filtering is aggressive on purpose. Asking for the data is not asking for
  // the argument about the data, so the lede, the traceability rule, the
  // entity explainer and the closing pitch all belong to Everything.
  const full = view === "all";
  const entitled = canReadCedarPress(user);

  // Arriving with a fragment (an article's "Make your own" lands on
  // /press#grove) scrolls to that section once it exists. Client routing
  // does not do this on its own, and the target is rendered by a child on a
  // later frame than this one, hence the deferral. The sections a fragment
  // can name all live in the Everything view, which is the arrival default.
  useEffect(() => {
    if (!hash) return;
    const frame = requestAnimationFrame(() => {
      document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
    });
    return () => cancelAnimationFrame(frame);
  }, [hash]);
  // The gate is a full-bleed split screen, so it renders without the page's
  // masthead and gutter: those belong to the reader's page, and a sign-in
  // that inherits them reads as a page with a form on it.
  if (!loading && !entitled) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }

  return (
    <div className="teim-rd teim-rd--paper">
      <div className={`cp${full ? " cp--deepfoot" : ""}`}>
        <header className="cp-mast">
          <span className="cp-mast__word">CEDAR PRESS</span>
          {/* Who made it and who sells it, said plainly. "A × partnership"
              left both questions open. */}
          <span className="cp-mast__of">
            Built by <a href={LUMECON_URL} target="_blank" rel="noreferrer">Lumecon</a>. Available
            exclusively through{" "}
            <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a>.
          </span>
          {entitled ? (
            <span className="cp-mast__user">
              {user.email}
              {" · "}
              <button type="button" className="cp-split__linkbtn" onClick={() => logout()}>
                Sign out
              </button>
            </span>
          ) : null}
        </header>

        {loading ? null : !entitled ? (
<PressGate user={user} />
        ) : (
          <>
        {/* Sticky, so the choice is available from anywhere on the page. */}
        <nav className="cp-view" aria-label="Show">
          <span className="cp-view__cap">Show</span>
          {VIEWS.map((option) => (
            <button
              type="button"
              key={option.id}
              className={`cp-chip${view === option.id ? " is-on" : ""}`}
              aria-pressed={view === option.id}
              onClick={() => setView(option.id)}
            >
              {option.label}
            </button>
          ))}
        </nav>

        {/* The headline is deliberately not the tier lines. It used to be
            "See what happened. Understand what drives it", which mirrored the
            two shelves exactly, and the cost of that showed up twice: every
            time the tiers were renamed or resorted, the hero had to be
            rewritten with them. It says what the product is for and lets the
            shelves below explain the ladder themselves. The mission line
            lives at the close.

            The whole hero belongs to Everything. A reader who has filtered to
            Data is past being told what the page is, and the shelf is the
            answer they asked for. */}
        {full ? (
          <section className="cp-hero">
            <h1>Know what&rsquo;s shaping Indian Country.</h1>
            <p>
              Original intelligence collections, data-driven insights, transparent research and
              Cedar, your AI economic analyst, built to make Indian Country easier to understand.
              Every collection begins with public records, is enhanced through original research
              and entity resolution and stays current as new information becomes available.
            </p>
          </section>
        ) : null}

        {/* The trust claim, near the top where it does its work. Each line is
            a link rather than a promise: a reader can check all three from
            here, which is the whole point of making the claim. */}
        {full ? (
        <section className="cp-trace" aria-label="Every figure is traceable">
          <h2 className="cp-trace__claim">Every figure is traceable.</h2>
          <ul className="cp-trace__list">
            <li>
              <button
                type="button"
                onClick={() => {
                  setView("data");
                  // Deferred: from the Articles view the shelves are not on the
                  // page yet when this handler runs, so scrolling in the same
                  // tick finds nothing and does nothing.
                  requestAnimationFrame(() => {
                    document.getElementById("catalog")?.scrollIntoView({ behavior: "smooth" });
                  });
                }}
              >
                <span className="cp-trace__tick" aria-hidden="true">&#10003;</span>
                Download the data
              </button>
            </li>
            <li>
              <Link to={PRESS_METHODS_PATH}>
                <span className="cp-trace__tick" aria-hidden="true">&#10003;</span>
                View the methodology
              </Link>
            </li>
            <li>
              <Link to={PRESS_METHODS_PATH}>
                <span className="cp-trace__tick" aria-hidden="true">&#10003;</span>
                See every source
              </Link>
            </li>
          </ul>
        </section>
        ) : null}

        {showArticles ? (
        <section className="cp-surf cp-surf--paper" id="briefs" aria-label="Latest research">
          <Contours strength={1} />
          <div className="cp-surf__in">
          <div className="cp-head">
            <span className="cp-sec__band">Latest research</span>
            <span className="cp-kind cp-kind--art">Articles</span>
          </div>
          {/* A front page, not a row of tiles: the newest brief leads at
              double width, the rest stack beside it, and growth appends to
              the stack with the archive living at TBN. */}
          <div className="cp-artgrid">
            <ArticleCard article={PRESS_ARTICLES[0]} />
            <div className="cp-artstack">
              {PRESS_ARTICLES.slice(1).map((article) => (
                <ArticleCard key={article.id} article={article} compact />
              ))}
              <a className="cp-artmore" href={TBN_URL} target="_blank" rel="noreferrer">
                Selected Cedar Press research also publishes with Tribal Business News →
              </a>
            </div>
          </div>
          {/* Sponsorship rule 5: never in a filtered view. The slot belongs to
              Everything; a reader who filtered to Articles asked for the
              briefs, and the inventory does not follow them there. */}
          {full ? <PressAd slot={AD_SLOT.BRIEFS} /> : null}
          </div>
        </section>
        ) : null}

        {/* The differentiator, said once and up front. Without it the
            catalog below reads as a repackaging of open data, which is what
            a reader will assume because the source records genuinely are
            public. The tiers are listed because "Native" covers several
            distinct relationships and merging them would be a claim the
            data does not support. */}
        {full ? (
        <section className="cp-surf cp-surf--pale cp-link" aria-label="What Cedar adds">
          <Halo strength={0.8} />
          <div className="cp-surf__in">
          <div className="cp-head">
            <span className="cp-sec__band">What Cedar adds</span>
            <span className="cp-kind cp-kind--data">About the collections</span>
          </div>
          <div className="cp-link__in">
            <h2 className="cp-link__claim">{NATIVE_LINKAGE.claim}</h2>
            <p className="cp-link__body">{NATIVE_LINKAGE.body}</p>
          </div>
          <p className="cp-link__hard">{NATIVE_LINKAGE.hard}</p>
          <ul className="cp-link__tiers">
            {NATIVE_LINKAGE.groups.map((group) => (
              <li key={group}>{group}</li>
            ))}
          </ul>
          <p>
            <Link className="cp-m__more" to={PRESS_METHODS_PATH}>
              See Cedar&rsquo;s entity methodology <span aria-hidden="true">&#8594;</span>
            </Link>
          </p>
          </div>
        </section>
        ) : null}

        {showData ? <PressShelf user={user} view={view} /> : null}

        {/* The end of the page, in two columns rather than three bands of
            stretched-out text. Left is what you give back: corrections,
            requests, and a citation when the data turns up in public. Right
            is where it goes next. Each column lights up on hover, so the
            two read as a choice rather than as leftover copy. */}
        {/* The ending. One closing statement and three quiet actions rather
            than two equal boxes: a page that has just argued for a maintained
            research product should end on the maintenance. */}
        {full ? (
        <section className="cp-surf cp-surf--deep cp-close" id="more" aria-label="What happens next">
          <Contours strength={1.2} />
          <div className="cp-close__in">
            <div className="cp-close__say">
              <h2 className="cp-close__head">The records change. Cedar changes with them.</h2>
              <p className="cp-close__body">
                New records, ownership changes, corrections and historical evidence arrive
                continuously, and every collection here is maintained against them. What you
                cited last quarter is still reproducible; what you cite next quarter will be
                better.
              </p>
            </div>
            <ul className="cp-new">
              {recentlyUpdated(3).map((release) => (
                <li className="cp-new__item" key={release.id}>
                  <b>{PRESS_CATALOG_BY_ID[release.id]?.name ?? release.id}</b>
                  <span className="cp-new__date">{formatUpdated(release.updated)}</span>
                </li>
              ))}
            </ul>
            <div className="cp-close__acts">
              <Link className="cp-close__act" to={PRESS_WHATS_NEW_PATH}>
                See what&rsquo;s new <span aria-hidden="true">&#8594;</span>
              </Link>
              <a
                className="cp-close__act"
                href="mailto:contact@lumecon.ai?subject=Cedar%20Press%20feedback"
              >
                Send feedback <span aria-hidden="true">&#8594;</span>
              </a>
              <a className="cp-close__act" href={appUrl("/app/grove")} target="_blank" rel="noreferrer">
                Explore Cedar Grove <span aria-hidden="true">&#8594;</span>
              </a>
            </div>
            {/* The mission line, kept as a mission line. It is the reason the
                product exists rather than a description of it, so it closes
                the page instead of opening it. */}
            <p className="cp-close__mission">
              <span>Why we build this</span>
              Making Indian Country impossible to overlook.
            </p>
          </div>
        </section>
        ) : null}

        <PressCedarFab />
          </>
        )}

        <footer className={`cp-foot${full ? " cp-foot--deep" : ""}`}>
          <div className="cp-foot__in">
          <span>
            <Link to={PRESS_METHODS_PATH}>Methods</Link>
            {" · "}
            <Link to={PRESS_REQUEST_PATH}>Tribal data request</Link>
            {" · "}
            <Link to={PRESS_RESEARCH_PATH}>Research access</Link>
            {" · "}
            <Link to={PRESS_WHATS_NEW_PATH}>What&rsquo;s new</Link>
          </span>
          <span>
            <a href={TBN_URL} target="_blank" rel="noreferrer">tribalbusinessnews.com</a>
            {" · "}
            <a href={LUMECON_URL} target="_blank" rel="noreferrer">lumecon.ai</a>
          </span>
          <span>Every collection carries its method · corrections reach every release they touch</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
