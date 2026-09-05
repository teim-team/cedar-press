// REVIEW OWNER: Havala
//
// Methods: why the data is credible.
//
// That is the whole job of this page. It is not where Cedar explains what it
// is, what a tier costs, or how to request records, and the previous version
// tried to do all of that arranged as a memo. Five sections, each carrying one
// argument, and the process is the dominant visual rather than seven cards in
// a row.
//
// Public on purpose: someone deciding whether to pay should be able to read
// exactly how the work is done first.

import { Link } from "react-router";
import { contactHref } from "../../features/grove/appLink.js";

import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import { PRESS_PATH, PRESS_REQUEST_PATH } from "../../features/grove/pressRoutes";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import {
  CREDIBILITY_DISCLAIMER,
  CREDIBILITY_STRIP,
  METHOD_COMMITMENTS,
  expertiseSentence,
} from "../../features/grove/pressMethod";
import { PRESS_CATALOG } from "../../features/grove/pressCatalog";
import { coverageLabel } from "../../features/grove/pressAccess";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { releaseFor } from "../../features/grove/pressReleases";
import { EcosystemDiagram, ProcessRail, EntityTimeline } from "./pressMethodSections";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";


const TRUST_ROW = [
  "Documented methodology",
  "Versioned releases",
  "Human review",
  "Source register",
  "Correction process",
];

export default function CedarPressMethods() {
  // The masthead carries the reader's profile and Sign out. These two pages
  // rendered `<PressMast section="..." />` with NO `user` and no
  // `onSignOut`, so a signed-in reader who navigated here lost the avatar
  // and the way out - the session was intact, the chrome just stopped
  // saying so. Articles and Data always passed both; these did not.
  const { user, logout } = useAuth();
  const entitled = canReadCedarPress(user);

  useDocumentTitle("Methods");
  useScrollToTop();
  // Sitewide arrival language: each argument fades in as the reader
  // reaches it.
  const fadeRoot = useFadeIn();
  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="methods" />

        {/* The opening argument, given room. The claim under it is the one
            sentence this page exists to earn, so it stands alone rather than
            being followed straight into a paragraph. */}
        <section className="cp-mh">
          <p className="cp-hero__access">How Cedar is built</p>
          <h1 className="cp-mh__title">Public records are only the beginning.</h1>
          <p className="cp-mh__sub">
            Cedar collections are maintained research products, built from fragmented public
            records, historical files, regulatory material and other sources that were never
            designed to work together.
          </p>
        </section>

        <p className="cp-mh__claim cp-fade">In many cases, the collection does not exist until Cedar builds it.</p>

        <section className="cp-msec cp-fade" aria-label="The process">
          <span className="cp-sec__band">The process</span>
          <h2 className="cp-msec__title">From scattered records to maintained intelligence.</h2>
          <ProcessRail />
          <p className="cp-msec__close">
            Every Cedar collection follows this pipeline, with collection-specific sources and
            resolution rules documented below.
          </p>
        </section>

        <section className="cp-msec cp-fade" aria-label="One connected system">
          <span className="cp-sec__band">One system</span>
          <h2 className="cp-msec__title">Built as one connected intelligence system.</h2>
          <EcosystemDiagram />
          <p className="cp-msec__close">
            The collections become more valuable because they were designed to work together.
          </p>
        </section>

        <section className="cp-msec cp-fade" aria-label="Maintenance">
          <span className="cp-sec__band">Maintenance</span>
          <h2 className="cp-msec__title">Accuracy has a time dimension.</h2>
          <p className="cp-msec__lede">
            A collection can be correct when published and wrong a year later if nobody maintains the
            organizations behind it. Cedar is built to stay current.
          </p>
          <EntityTimeline />
          <p className="cp-msec__close">
            Cedar preserves both current identity and the lineage needed to read older records
            correctly.
          </p>
        </section>

        {/* The philosophy above; the specifics here. A researcher's next
            question after "how does Cedar work" is "how was THIS collection
            built", and the answer is assembled from the same declarations the
            product runs on — the catalog, the launch descriptors and the
            release log — so a row cannot say something the collection does
            not. Ask Cedar sits on each row because the profile behind the row
            is exactly what Cedar answers from. */}
        <section className="cp-msec cp-fade" aria-label="Methods by collection">
          <span className="cp-sec__band">Methods by collection</span>
          <h2 className="cp-msec__title">The specifics, collection by collection.</h2>
          <div className="cp-mbc">
            {PRESS_CATALOG.map((entry) => {
              const launch = LAUNCH_COLLECTION.find((dataset) => dataset.id === entry.id);
              const release = releaseFor(entry.id);
              return (
                <details className="cp-mbc__row" key={entry.id}>
                  <summary>
                    <span className="cp-mbc__name">{entry.name}</span>
                    <span className="cp-mbc__meta">
                      {release ? `${release.version} · ` : ""}
                      {coverageLabel(entry)}
                    </span>
                  </summary>
                  <div className="cp-mbc__body">
                    <p>{entry.blurb}</p>
                    <p>
                      <span className="cp-mbc__cap">Entity resolution</span>
                      {entry.linkage}
                    </p>
                    {launch ? (
                      <p>
                        <span className="cp-mbc__cap">Method</span>
                        {launch.method}
                      </p>
                    ) : null}
                    <p className="cp-mbc__facts">
                      {launch ? <>Sources: {launch.sources} &middot; </> : null}
                      {coverageLabel(entry)}
                      {release ? (
                        <>
                          {" "}&middot; {release.cadence} &middot; current release {release.version}
                        </>
                      ) : null}
                    </p>
                    <button
                      type="button"
                      className="cp-read__cedar"
                      onClick={() =>
                        window.dispatchEvent(
                          new CustomEvent("cedar:ask-collection", {
                            detail: { id: entry.id, name: entry.name },
                          }),
                        )
                      }
                    >
                      Ask Cedar about this collection <span aria-hidden="true">&#8594;</span>
                    </button>
                  </div>
                </details>
              );
            })}
          </div>
        </section>

        {/* Restraint, stated as commitments rather than left implicit: the
            things Cedar could do to look more complete and does not. */}
        <section className="cp-msec cp-fade" aria-label="What Cedar will not do">
          <span className="cp-sec__band">Commitments</span>
          <h2 className="cp-msec__title">What Cedar will not do.</h2>
          <ul className="cp-wont">
            {METHOD_COMMITMENTS.map((item) => (
              <li key={item.id}>{item.text}</li>
            ))}
          </ul>
        </section>

        <section className="cp-msec cp-fade" aria-label="Expertise and accountability">
          <span className="cp-sec__band">Expertise</span>
          <h2 className="cp-msec__title">Built by people who know the systems.</h2>
          <div className="cp-exp">
            <div>
              <p className="cp-msec__lede">
                Cedar is built by Indigenous researchers and a team with experience at the Federal
                Reserve Board and the Federal Reserve Banks of Minneapolis and Philadelphia,
                academic backgrounds spanning MIT, Oxford, Cornell, Brown, Dartmouth and Yale, and
                decades of combined work in Indian Country.
              </p>
              {/* The domains are read from the strip rather than typed: this
                  sentence named gaming for a week after the shelf stopped
                  selling it, because nothing held the two together. */}
              <p className="cp-exp__body">
                {expertiseSentence()} each have different definitions, reporting systems and
                historical quirks. Reliable data requires knowing how to process the records
                and what those records mean.
              </p>
            </div>
            <div className="cp-exp__strip">
              {CREDIBILITY_STRIP.map((group) => (
                <div key={group.id}>
                  <span className="cp-exp__cap">{group.label}</span>
                  <span className="cp-exp__names">{group.names.join(" · ")}</span>
                </div>
              ))}
              <p className="cp-exp__note">{CREDIBILITY_DISCLAIMER}</p>
            </div>
          </div>
          <ul className="cp-trust">
            {TRUST_ROW.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="cp-msec__close">
            <a className="cp-m__more" href={contactHref("Cedar correction")}>
              Found something wrong? Send a correction <span aria-hidden="true">&#8594;</span>
            </a>
          </p>
        </section>

        <PressFoot />
        <PressCedarFab />
      </main>
    </div>
  );
}
