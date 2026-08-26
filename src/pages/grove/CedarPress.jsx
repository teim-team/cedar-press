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
import { appUrl } from "../../features/grove/appLink.js";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { PRESS_CATALOG_BY_ID } from "../../features/grove/pressCatalog";
import { formatUpdated, recentlyUpdated } from "../../features/grove/pressReleases";
import { Contours } from "./pressAtmosphere";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";
import PressHub from "./PressHub";

export default function CedarPress() {
  useDocumentTitle();
  const { user, loading, logout } = useAuth();
  const entitled = canReadCedarPress(user);

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
      <main id="cp-main" className="cp cp-page cp--screens">
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="home" />

        {loading ? null : (
          <>
        {/* The headline is deliberately not the tier lines: it says what the
            product is for and lets the pages behind the doors explain the
            ladder themselves. The mission line lives at the close. */}
        <section className="cp-hero cp-screen">
          <h1>Know what&rsquo;s shaping Indian Country.</h1>
          <p>
            Original intelligence collections, data-driven insights, transparent research and
            Cedar, your AI economic analyst, built to make Indian Country easier to understand.
            Every collection begins with public records, is enhanced through original research
            and entity resolution and stays current as new information becomes available.
          </p>
        </section>


        <PressHub />

        {/* The ending. One closing statement and three quiet actions rather
            than two equal boxes: a page that has just argued for a maintained
            research product should end on the maintenance. */}
        <section className="cp-surf cp-surf--deep cp-close cp-screen" id="more" aria-label="What happens next">
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
            <ul className="cp-new">
              {recentlyUpdated(3).map((release) => (
                <li className="cp-new__item" key={release.id}>
                  <b>{PRESS_CATALOG_BY_ID[release.id]?.name ?? release.id}</b>
                  <span className="cp-new__date">{formatUpdated(release.updated)}</span>
                </li>
              ))}
            </ul>
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
            {/* The mission line, kept as a mission line. It is the reason the
                product exists rather than a description of it, so it closes
                the page instead of opening it. */}
            <p className="cp-close__mission">
              <span>Why we build this</span>
              Making Indian Country impossible to overlook.
            </p>
          </div>
        </section>

        <PressCedarFab />
          </>
        )}

        <PressFoot />
      </main>
    </div>
  );
}
