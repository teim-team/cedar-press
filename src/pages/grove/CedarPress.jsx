// REVIEW OWNER: Havala
//
// Cedar Press: the reader's front page.
//
// Behind an entitlement, not public. `canReadCedarPress` decides whether this
// renders the hub or hands off to PressGate, and the two never appear
// together: the gate is a full-bleed split screen with no masthead, because a
// sign-in that inherits the page chrome reads as a page with a form on it.
//
// THE HUB SHAPE
// The reader used to be one long page carrying everything; it curated well
// on a wide screen and read as a quarter hour of thumb on a phone. Now the
// front page states what the product is (the hero and the traceability
// claim), opens four doors (articles, data, what's new, methods — see
// PressHub), and closes on the maintenance promise. The articles and the
// shelves live behind their doors, on pages of their own, identical on
// desktop and phone.
//
// Built from the app's own tokens, so this page cannot drift from what
// subscribers see inside Grove.

// The app's stylesheet order, so the Cedar widget markup below is styled by
// exactly the rules that style it inside the product: index.css base,
// redesign.css retheme, then this page's own layout.
import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { appUrl } from "../../features/grove/appLink.js";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { AD_SLOT } from "../../features/grove/pressAds";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog";
import { anchorOf, formatUpdated, latestRelease, recentlyUpdated } from "../../features/grove/pressReleases";
import { Contours } from "./pressAtmosphere";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressAd from "./PressAd";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { PRESS_ARTICLES } from "../../features/grove/pressArticles";
import {
  PRESS_DATA_PATH,
  PRESS_WHATS_NEW_PATH,
  pressArticlePath,
} from "../../features/grove/pressRoutes";
import PressGate from "./PressGate";
import PressHub from "./PressHub";

export default function CedarPress() {
  useDocumentTitle();
  const { user, loading, logout } = useAuth();
  const entitled = canReadCedarPress(user);
  // Sections arrive as they enter the viewport, sitewide language.
  const fadeRoot = useFadeIn();

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

  // Newest hosted brief: the strip is newest-first, and an external piece
  // opens on TBN, which is not "read it here".
  const latestBrief = PRESS_ARTICLES.find((article) => article.hosted);
  // Cedar's suggestions on the overview: one real question per level, each
  // already scoped to a collection so every suggestion is answerable today.
  const cedarExamples = [
    { q: "How was this collection constructed?", scope: LAUNCH_COLLECTION[1] },
    { q: "What are its headline figures?", scope: LAUNCH_COLLECTION[2] },
    { q: "What does this collection cover?", scope: LAUNCH_COLLECTION[3] },
  ].map((item) => ({ q: item.q, scope: { id: item.scope.id, name: item.scope.name } }));
  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page cp--screens cp--deepfoot" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="home" />

        {loading ? null : (
          <>
        {/* Screen one: what this is, and where to go, together. Apart they
            were two thin bands of content floating in white; the statement is
            what the six sections are an answer to, so it sits above them and
            the pair fills a screen between them.

            The headline is deliberately not the tier lines: it says what the
            product is for and lets the pages behind the doors explain the
            ladder themselves. The mission line lives at the close. */}
        <div className="cp-screen cp-open">
          <section className="cp-hero cp-fade">
            <h1>Know what&rsquo;s shaping Indian Country.</h1>
            <p>
              Original intelligence collections, data-driven insights, transparent research and
              Cedar, your AI economic analyst, built to make Indian Country easier to understand.
              Every collection begins with public records, is enhanced through original research
              and entity resolution and stays current as new information becomes available.
            </p>
          </section>
          {/* The first question a signed-in reader has is "what do I do
              now?", and six doors answer "what exists" without answering
              that. Four verbs, each real: the newest hosted brief is looked
              up, not hardcoded, and Ask Cedar opens the assistant that can
              answer the other three. */}
          <nav className="cp-start cp-fade" aria-label="Start here">
            <button
              type="button"
              className="cp-start__act"
              onClick={() => window.dispatchEvent(new CustomEvent("cedar:open"))}
            >
              Ask Cedar <span aria-hidden="true">&#8594;</span>
            </button>
            <Link className="cp-start__act" to={PRESS_DATA_PATH}>
              Explore the collections <span aria-hidden="true">&#8594;</span>
            </Link>
            {latestBrief ? (
              <Link className="cp-start__act" to={pressArticlePath(latestBrief.id)}>
                Read the latest brief <span aria-hidden="true">&#8594;</span>
              </Link>
            ) : null}
            <Link className="cp-start__act" to={PRESS_WHATS_NEW_PATH}>
              See what changed <span aria-hidden="true">&#8594;</span>
            </Link>
          </nav>
          <PressHub user={entitled ? user : null} />
        </div>

        {/* Screen two: the close and the footer, as one ending. The ending is
            one closing statement and two quiet actions rather than two equal
            boxes — a page that has just argued for a maintained research
            product should end on the maintenance — and the footer is the last
            of it rather than a separate strip below the last of it. */}
        <div className="cp-screen cp-end">
        {/* Sponsorship rides the ending, not the arrival: a signed-in
            reader's first screen is for using the product, and the close is
            where a page pauses anyway. Still inside a region rather than on
            a seam — rule 4 — and the overview names no figures, so a unit
            is nowhere near a number. */}
        <PressAd slot={AD_SLOT.OVERVIEW} />
        <section className="cp-surf cp-surf--deep cp-close cp-fade" id="more" aria-label="What happens next">
          <Contours strength={1.2} />
          <div className="cp-close__in">
            <div className="cp-close__say">
              <h2 className="cp-close__head">Nothing here is a snapshot.</h2>
              <p className="cp-close__body">
                Records are added, ownership changes and corrections come in every week, and
                the collections are kept current against them. A figure you cited last quarter
                still reproduces.
              </p>
            </div>
            {/* The three most recently changed collections, read from the
                release record, each a door into What's New at that release's
                permalink, and a fourth line into the whole feed. The claim
                beside them is that the collections keep moving; a reader who
                wants to check it should be one click from the evidence. */}
            <ul className="cp-new">
              {recentlyUpdated(3).map((release) => {
                const latest = latestRelease(release.id);
                const to = latest
                  ? `${PRESS_WHATS_NEW_PATH}#${anchorOf({ id: release.id, version: latest.version })}`
                  : PRESS_WHATS_NEW_PATH;
                return (
                  <li className="cp-new__item" key={release.id}>
                    <Link className="cp-new__link" to={to}>
                      <b>{PRESS_CATALOG_BY_ID[release.id]?.name ?? release.id}</b>
                      <span className="cp-new__date">{formatUpdated(release.updated)}</span>
                    </Link>
                  </li>
                );
              })}
              <li className="cp-new__item cp-new__more">
                <Link className="cp-new__link" to={PRESS_WHATS_NEW_PATH}>
                  See every release <span aria-hidden="true">&#8594;</span>
                </Link>
              </li>
            </ul>
            {/* Under the statement, in its column, rather than on a rule of
                their own across the page. Two links are not a section. */}
            <div className="cp-close__acts">
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
          </div>
        </section>
          <PressFoot flush />
        </div>

        <PressCedarFab examples={cedarExamples} />
          </>
        )}
      </main>
    </div>
  );
}
