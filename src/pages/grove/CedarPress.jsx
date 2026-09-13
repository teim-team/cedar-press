// REVIEW OWNER: Havala
//
// Cedar Press: the reader's front page.
//
// Behind an entitlement, not public. `canReadCedarPress` decides whether this
// renders the page or hands off to PressGate, and the two never appear
// together: the gate is a full-bleed split screen with no masthead, because a
// sign-in that inherits the page chrome reads as a page with a form on it.
//
// THE PAGE IS THE COLLECTIONS
// This used to be a hub: a headline, four pill links, six identical squares
// naming the sections, and a close. A subscriber landing on it saw nothing
// they had paid for until the second click. Now the front page is built the
// way the collections page is, around the collections themselves: one
// promise, then every collection on its shelf with a stage beside the list
// showing six real records of the one in hand (PressCollectionsStage). The
// other sections follow as a ledger (PressDoors), and the page closes on
// the maintenance promise. The full viewer, the downloads and the Cedar
// Grove case stay on /data; the front page opens onto them.
//
// Built from the design system's own tokens (index.css base, redesign.css
// retheme, then press.css, imported once in main.jsx in that order).
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { appUrl, contactHref } from "../../features/grove/appLink.js";
import { canReadCedarPress, coverageFrom } from "../../features/grove/pressAccess";
import { AD_SLOT } from "../../features/grove/pressAds";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { PRESS_CATALOG_BY_ID, STOREFRONT_CATALOG, spellCount } from "../../features/grove/pressCatalog";
import { anchorOf, formatUpdated, latestRelease, recentlyUpdated } from "../../features/grove/pressReleases";
import { Contours } from "./pressAtmosphere";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressAd from "./PressAd";
import { LAUNCH_COLLECTION, LAUNCH_ROWS_TOTAL } from "../../features/grove/collection";
import { PRESS_DATA_PATH, PRESS_WHATS_NEW_PATH } from "../../features/grove/pressRoutes";
import PressCollectionsStage from "./PressCollectionsStage";
import PressDoors from "./PressDoors";
import PressGate from "./PressGate";

const capitalise = (word) => word[0].toUpperCase() + word.slice(1);

export default function CedarPress() {
  // The door is the one page every visitor and every crawler reaches.
  useDocumentTitle(undefined, { index: true });
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

  // The facts under the promise, each read from the catalog or the release
  // record. The earliest year is the deepest single collection, so the line
  // says "as far back as", never "since": the rest start later and two of
  // them are rosters with no start at all.
  const starts = STOREFRONT_CATALOG.map((entry) => coverageFrom(entry)).filter(Boolean);
  const earliest = starts.length ? Math.min(...starts) : null;
  const newest = recentlyUpdated(1)[0] ?? null;

  // Cedar's suggestions on the overview: one real question per level, each
  // already scoped to a collection so every suggestion is answerable today.
  const cedarExamples = [
    { q: "How was this collection constructed?", scope: LAUNCH_COLLECTION[1] },
    { q: "What are its headline figures?", scope: LAUNCH_COLLECTION[2] },
    { q: "What does this collection cover?", scope: LAUNCH_COLLECTION[3] },
  ].map((item) => ({ q: item.q, scope: { id: item.scope.id, name: item.scope.name } }));

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page cp-home cp--deepfoot" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="home" />

        {loading ? null : (
          <>
            {/* One promise, and what stands behind it. The headline says what
                the product is for; the facts line says what it is made of,
                in numbers the catalog and the release record supply. */}
            <section className="cp-lead cp-fade" aria-label="Cedar Press">
              <p className="cp-lead__kicker">Cedar Press · Original intelligence collections</p>
              <h1>Know what&rsquo;s shaping Indian Country.</h1>
              <div className="cp-lead__aside">
                <p className="cp-lead__sub">
                  {capitalise(spellCount(STOREFRONT_CATALOG.length))} collections, each begun
                  from public records, resolved to the Native entities behind them and kept
                  current as new material arrives. Every record below is real; open a collection
                  to see what it holds.
                </p>
                <div className="cp-lead__acts">
                  <Link className="cp-btn" to={PRESS_DATA_PATH}>
                    Browse every collection <span aria-hidden="true">&#8594;</span>
                  </Link>
                  <button
                    type="button"
                    className="cp-btn cp-btn--quiet"
                    onClick={() => window.dispatchEvent(new CustomEvent("cedar:open"))}
                  >
                    Ask Cedar <span aria-hidden="true">&#8594;</span>
                  </button>
                </div>
              </div>
              <ul className="cp-facts" aria-label="What Cedar Press holds">
                <li><b>{STOREFRONT_CATALOG.length}</b> collections</li>
                {LAUNCH_ROWS_TOTAL ? <li><b>{LAUNCH_ROWS_TOTAL.toLocaleString("en-US")}</b> records</li> : null}
                {earliest ? <li>records as far back as <b>{earliest}</b></li> : null}
                {newest ? <li>latest release <b>{formatUpdated(newest.updated)}</b></li> : null}
              </ul>
            </section>

            <PressCollectionsStage user={entitled ? user : null} />

            <PressDoors signedIn={entitled} />

            {/* Sponsorship rides the ending, not the arrival: a signed-in
                reader's first screen is for using the product, and the close is
                where a page pauses anyway. Still inside a region rather than on
                a seam — rule 4 — and the overview names no figures near it, so
                a unit is nowhere near a number. */}
            <PressAd slot={AD_SLOT.OVERVIEW} />

            {/* The close and the footer, as one ending: one statement and a
                few quiet actions, because a page that has just shown a
                maintained research product should end on the maintenance. */}
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
                    permalink, and a fourth line into the whole feed. */}
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
                {/* The errands that used to be two of the six squares: plans
                    are bought at Tribal Business News, feedback goes to the
                    desk, and Grove is the other product. */}
                <div className="cp-close__acts">
                  <a className="cp-close__act" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                    Plans and access <span aria-hidden="true">&#8594;</span>
                  </a>
                  <a className="cp-close__act" href={contactHref("Cedar Press feedback")}>
                    Send feedback <span aria-hidden="true">&#8594;</span>
                  </a>
                  <a className="cp-close__act" href={appUrl("/app/grove")} target="_blank" rel="noreferrer">
                    Explore Cedar Grove <span aria-hidden="true">&#8594;</span>
                  </a>
                </div>
              </div>
            </section>
            <PressFoot flush />

            <PressCedarFab examples={cedarExamples} />
          </>
        )}
      </main>
    </div>
  );
}
