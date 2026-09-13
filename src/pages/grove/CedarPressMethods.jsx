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
import {
  EcosystemDiagram,
  FeedbackLoop,
  IdentityPair,
  LinkageMoves,
  MethodsByCollection,
  ProcessRail,
} from "./pressMethodSections";
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

        {/* THE ARGUMENT THIS PAGE EXISTS FOR.
            Everything above says the records are gathered carefully. This says
            why the result is one collection rather than twelve datasets, and it
            is the only section whose claims a competitor would have to match
            rather than buy. The two identifiers are load-bearing, so they are
            named, shown at transcription size and checked against the published
            register by `pressIdentity.test.js`. */}
        <section className="cp-msec cp-fade" aria-label="The identity layer">
          <span className="cp-sec__band">Identity</span>
          <h2 className="cp-msec__title">Two identifiers, maintained by hand where it counts.</h2>
          <p className="cp-msec__lede">
            No public system will tell you that a vendor in a federal contract is owned by a
            nation, and none of the systems Cedar reads shares a key with any of the others.
            Cedar assigns its own and keeps it current. A Cedar entity id names a government, an
            agency, an NHO or an enterprise a nation owns. A Cedar business id names a firm as a
            source named it, and then the resolved firm those sightings add up to. Most
            enterprises carry both.
          </p>
          <IdentityPair />
          <p className="cp-msec__close">
            A firm that is Native-owned without being owned by a nation gets the business id from
            the first sighting. If a nation acquires it later, the history is already there. The
            published register carries those firms by identifier with their names withheld, which
            is how a private business can be tracked for continuity without being listed in a
            directory.
          </p>
        </section>

        <section className="cp-msec cp-fade" aria-label="What the identifiers make possible">
          <span className="cp-sec__band">Linkage</span>
          <h2 className="cp-msec__title">Start anywhere. The answer still holds together.</h2>
          <p className="cp-msec__lede">
            Any keyword, any agency, any year, any nation. What comes back is one
            organization&rsquo;s whole footprint rather than the rows that happened to spell its
            name your way, because the identifier was already on every row before the question
            was asked.
          </p>
          <LinkageMoves />
        </section>

        <section className="cp-msec cp-fade" aria-label="How the collections improve">
          <span className="cp-sec__band">The loop</span>
          <h2 className="cp-msec__title">It gets more accurate the longer it runs.</h2>
          <p className="cp-msec__lede">
            Cedar builds and trains models on its own resolved records. A researcher rules on
            every final output. The ruling goes back into the evidence the models read, so the
            collection is the input to the next pass over it.
          </p>
          <FeedbackLoop />
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
          <MethodsByCollection />
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
