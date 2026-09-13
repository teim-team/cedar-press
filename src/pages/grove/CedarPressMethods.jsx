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
import { WITHHELD_NOTE } from "../../features/grove/pressIdentity";
import {
  EcosystemDiagram,
  FeedbackLoop,
  IdentityPair,
  KeptOutside,
  LinkageMoves,
  MethodsByCollection,
  ProcessRail,
  WhyBoth,
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

        {/* THE HEADLINE.
            "Public records are only the beginning" was the owner's call to
            cut, and he was right: it says the records are a starting point
            and stops, which describes a gap rather than a product, and every
            data company on earth could put it on a page. The argument is
            narrower and much harder to copy. There is no shortage of records
            about Indian Country. There is no key in any of them that says
            which organization a row belongs to, so nothing can be added up.
            Cedar mints that key and maintains it. Say that.

            The mark fills the top right, which was empty from the masthead
            down to the pull quote. */}
        <section className="cp-mh">
          <p className="cp-hero__access">How Cedar is built</p>
          <h1 className="cp-mh__title">The records exist. Nothing in them agrees on who is who.</h1>
          <div className="cp-mh__right">
            <p className="cp-mh__sub">
              Federal awards, tax filings, royalty statements, dockets, legislation and each
              nation&rsquo;s own publications hold an enormous amount about Indian Country, and no two
              of them identify an organization the same way. Cedar assigns a permanent identifier
              to every Native government, enterprise and firm it can resolve, and maintains it
              through renames, acquisitions and changes in legal status. That identifier is what
              turns twelve datasets into one collection a question can be asked of.
            </p>
          </div>
        </section>

        {/* The mark rides the pull quote rather than the headline row. In the
            headline row it either pushed the paragraph down, reopening the
            gap under the headline, or sat on top of the paragraph's first two
            lines. Here it fills the largest empty area on the page and
            collides with nothing. */}
        <div className="cp-mh__claimrow cp-fade">
          <p className="cp-mh__claim">In many cases, the collection does not exist until Cedar builds it.</p>
          <img className="cp-mh__mark" src="/brand/lumecon-logo-mark-teal.png" alt="" width="360" height="360" />
        </div>

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
            A 990 says who filed it. A royalty statement says who was paid. A docket says who
            appeared. None of them says whether those three are the same nation, and no public
            system will tell you. Cedar assigns the key none of them carries and keeps it
            current, in two namespaces that never mix. A Cedar entity id names one canonical
            Native entity. A Cedar business id names one distinct business or enterprise. The
            ownership between them is a dated relationship carrying its source, which is what
            keeps a nation and the company it owns from collapsing into one row.
          </p>
          <IdentityPair />
          {/* The owner's challenge, 2026-09-13: is it wrong that Cedar does
              not publish what it resolves? It would be. The earlier sentence
              here said the names are withheld and stopped, which described a
              product that resolves firms and then hides them. What is
              actually withheld is much narrower, and the line between the
              two cases is a judgement worth showing. WITHHELD_NOTE holds the
              wording, with the rule it comes from cited beside it. */}
          <p className="cp-msec__close">
            A firm that is Native-owned without being owned by a nation gets the business id from
            the first sighting. If a nation acquires it later, the history is already there.
          </p>
          <p className="cp-msec__aside">{WITHHELD_NOTE}</p>
        </section>

        {/* WHY TWO NAMESPACES. The owner's worked example, and the argument
            the rest of the page rests on: one id space collapses an
            enterprise into its tribal owner, and then "what has this nation
            been involved in" and "what has this enterprise won" become the
            same query with the same wrong answer. */}
        <section className="cp-msec cp-fade" aria-label="Why both identifiers">
          <span className="cp-sec__band">Two subjects</span>
          <h2 className="cp-msec__title">A nation and the company it owns are not one thing.</h2>
          <p className="cp-msec__lede">
            A Native entity can own or operate a business. That does not make the business and
            the entity the same subject, and a single identifier space is a decision to treat
            them as one. Cedar keeps two, and puts the ownership between them where it can carry
            dates and a source.
          </p>
          <WhyBoth />
        </section>

        <section className="cp-msec cp-fade" aria-label="What the identifiers do not carry">
          <span className="cp-sec__band">Kept outside</span>
          <h2 className="cp-msec__title">Anything that can change stays out of the identifier.</h2>
          <p className="cp-msec__lede">
            The reason a Cedar id is worth building a collection on is everything it refuses to
            hold. An identifier that encodes ownership has to be rewritten when a firm is sold;
            one that encodes a state has to be rewritten when the firm moves. Cedar&rsquo;s encode
            nothing, so they never move.
          </p>
          <KeptOutside />
        </section>

        <section className="cp-msec cp-fade" aria-label="What the identifiers make possible">
          <span className="cp-sec__band">Linkage</span>
          <h2 className="cp-msec__title">Twelve datasets stop behaving like twelve datasets.</h2>
          <p className="cp-msec__lede">
            Start from any keyword, agency, year or nation. What comes back is one
            organization&rsquo;s whole footprint rather than the rows that happened to spell its
            name your way, because the identifier was already on every row before the question
            was asked. An answer in one collection is a key into the others, so a finding can be
            followed rather than only reported.
          </p>
          <LinkageMoves />
          <p className="cp-msec__close">
            That is the difference between a shelf of files and a collection: the files hold
            records, and the collection holds an organization.
          </p>
        </section>

        <section className="cp-msec cp-fade" aria-label="How the collections improve">
          <span className="cp-sec__band">The loop</span>
          <h2 className="cp-msec__title">And the identifiers are what let Cedar answer you.</h2>
          <p className="cp-msec__lede">
            A model reading twelve unjoined files can retrieve text. A model reading an
            identified collection can count, compare and trace, because the rows already agree on
            who they are about. Cedar builds and trains its own models on its own resolved
            records, a researcher rules on every final output, and the ruling goes back into the
            evidence the models read. The collection is the input to the next pass over it, so
            the specific questions it can answer get more specific over time.
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
