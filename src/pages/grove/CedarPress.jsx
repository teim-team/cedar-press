// REVIEW OWNER: Havala
//
// Cedar Press: the reader's front page.
//
// Behind an entitlement, not public. `canReadCedarPress` decides whether this
// renders the hub or hands off to PressGate, and the two never appear
// together: the gate is a full-bleed split screen with no masthead, because a
// sign-in that inherits the page chrome reads as a page with a form on it.
//
// THE BRIEFING SHAPE
// The reader used to be one long page carrying everything; then it was six
// tiles opening six doors, which is the masthead's nav bar restated
// underneath itself. It is a briefing now (`PressBriefing`): the newest
// research, the three newest releases, the collection that just moved and
// one question about it, then the subscriber priorities and the maintenance
// promise. Every line of it is read from the release record and the article
// list rather than written, so it cannot fall out of step with the product.
//
// Built from the design system's own tokens (index.css base, redesign.css
// retheme, then press.css, imported once in main.jsx in that order).
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { GROVE_MARKETING_URL, contactHref } from "../../features/grove/appLink.js";
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
import { PRESS_WHATS_NEW_PATH } from "../../features/grove/pressRoutes";
import PressGate from "./PressGate";
import PressBriefing from "./PressBriefing";
import PressPrioritiesBlock from "./PressPrioritiesBlock";

export default function CedarPress() {
  // The door is the one page every visitor and every crawler reaches.
  useDocumentTitle(undefined, { index: true });
  const { user, loading } = useAuth();
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
        <PressMast section="home" />

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
          {/* ONE INTRODUCTION, ONE ACTION, THEN THE DOORS.
              Review, 2026-09-15: "you have the top navigation, four central
              action buttons, and six large section tiles. Several take users
              to the same places." Three of the four buttons went to a tile
              directly beneath them; the paragraph stacked original
              intelligence, data-driven insights, transparent research, an AI
              analyst, documented sources, original research again, entity
              resolution and ongoing updates — an argument for buying a
              product the reader has already bought. Ask Cedar stays, because
              it is the one thing here that is not a door. */}
          {/* THE HEADLINE, AND THEN THE BRIEFING THAT ANSWERS IT.
              The deck under it read "Browse the collections, read the
              research, and ask Cedar about any of it" — a description of the
              navigation bar, three inches under the navigation bar. The Ask
              Cedar button went with it: the briefing's own question is
              scoped to a collection and therefore answerable, and the
              launcher is on every page regardless. What is left is the
              premise, at the size of a premise rather than of a poster. */}
          <section className="cp-hero cp-hero--brief cp-fade">
            <h1>Know what&rsquo;s shaping Indian Country.</h1>
          </section>
          {/* THE BRIEFING, WHERE THE NAVIGATION USED TO BE REPEATED.
              `PressHub` drew six cards — Collections, Research Briefs,
              Priorities, What's new, Methods, Plans — which is the masthead's
              nav bar restated underneath itself as tiles. A reader who has
              signed in has already chosen this product; what they do not
              know is what moved. Every line of the briefing is read from the
              release record and the article list, so it cannot go stale. */}
          <PressBriefing />
          <PressPrioritiesBlock signedIn={entitled} />
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
                href={contactHref("Cedar Press feedback")}
              >
                Send feedback <span aria-hidden="true">&#8594;</span>
              </a>
              <a className="cp-close__act" href={GROVE_MARKETING_URL} target="_blank" rel="noreferrer">
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
