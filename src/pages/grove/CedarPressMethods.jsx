// REVIEW OWNER: Havala
//
// Methods: why the data is credible.
//
// That is the whole job of this page. It is not where Cedar explains what it
// is, what a tier costs, or how to request records.
//
// ============================================================================
// REBUILT 2026-09-14, on the owner's reading: "the methods page needs so much
// work, not sure why the logo is randomly there, and there is just so much
// text. It needs to be displayed better and hidden unless wanted. Just too
// overwhelming — perhaps the worst page. Can use more icons and buttons."
// ============================================================================
//
// Three things were wrong and all three were the same thing: the page asked
// to be READ, front to back, before it would answer anything.
//
// 1. THE MARK IS GONE. A 360px logo sat beside the pull quote to fill an
//    empty area. Decoration placed to fill space is what the empty space was
//    telling you: the space was the page's, and the argument should use it.
//
// 2. TEN CHAPTERS, ONE INDEX. Every section is now a numbered chapter with
//    its own mark, and the index at the top is the marks: a reader who came
//    to check one thing — how a record reaches an entity, what the coverage
//    figure counts — jumps to it instead of scrolling past nine arguments.
//    The index follows the reader down the page.
//
// 3. THE PROSE IS FOLDED, THE DRAWINGS ARE NOT. Each chapter now leads with
//    one claim and the diagram that makes it. The paragraph that used to
//    stand between the two sits behind "The reasoning", closed. Nothing is
//    deleted and nothing is summarised — a reader who wants the argument
//    opens it, and a reader checking a fact never has to.
//
// Everything a chapter asserts still comes from a declared module
// (pressMethod, pressIdentity, pressEcosystem, the catalog, the launch
// descriptors, the release log), so a chapter cannot say something the
// product does not.
//
// Public on purpose: someone deciding whether to pay should be able to read
// exactly how the work is done first.

import { useEffect, useState } from "react";
import { Link } from "react-router";
import { contactHref } from "../../features/grove/appLink.js";

import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";

import { PRESS_DATA_PATH, PRESS_REQUEST_PATH } from "../../features/grove/pressRoutes";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import {
  CREDIBILITY_DISCLAIMER,
  CREDIBILITY_STRIP,
  METHOD_COMMITMENTS,
  expertiseSentence,
} from "../../features/grove/pressMethod";
import { LINKAGE_COVERAGE, WITHHELD_NOTE } from "../../features/grove/pressIdentity";
import {
  EcosystemDiagram,
  FeedbackLoop,
  IdentityPair,
  KeptOutside,
  LinkageMoves,
  MethodsByCollection,
  ProcessRail,
  UnlinkedReasons,
  WhyBoth,
} from "./pressMethodSections";
import {
  ByCollectionIcon,
  ExpertiseIcon,
  IdentityIcon,
  LinkageIcon,
  LoopIcon,
  ProcessIcon,
  SubjectsIcon,
} from "./pressMethodIcons";
import Explain from "./Explain";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";

const TRUST_ROW = [
  "Documented methodology",
  "Versioned releases",
  "Human review",
  "Source register",
  "Correction process",
];

/**
 * The chapters, in order, and what the index calls them.
 *
 * `label` is the index's word and is deliberately shorter than the chapter's
 * own headline: an index of ten full sentences is a second page to read.
 */
const CHAPTERS = [
  { id: "sources", label: "Sources and matching", icon: ProcessIcon },
  { id: "ids", label: "Entity and business IDs", icon: IdentityIcon },
  { id: "ownership", label: "Ownership and relationships", icon: SubjectsIcon },
  { id: "linkage", label: "What is linked, and what is not", icon: LinkageIcon },
  { id: "updates", label: "Updates and corrections", icon: LoopIcon },
  { id: "collections", label: "By collection", icon: ByCollectionIcon },
  { id: "team", label: "Who builds it", icon: ExpertiseIcon },
];

const anchorId = (id) => `m-${id}`;

/**
 * Which chapter the reader is in, for the index.
 *
 * The topmost chapter intersecting the upper half of the window wins, which
 * is what a reader would say they are looking at. Rebuilt on nothing: the
 * chapters are static, so one observer for the life of the page.
 */
function useCurrentChapter() {
  const [current, setCurrent] = useState(CHAPTERS[0].id);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return undefined;
    const seen = new Map();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) seen.set(entry.target.id, entry.isIntersecting);
        const here = CHAPTERS.find((chapter) => seen.get(anchorId(chapter.id)));
        if (here) setCurrent(here.id);
      },
      // The top band of the window: a chapter is "current" once its head
      // reaches the reading line, not when its foot is still on screen.
      { rootMargin: "-12% 0px -62% 0px" },
    );
    for (const chapter of CHAPTERS) {
      const node = document.getElementById(anchorId(chapter.id));
      if (node) observer.observe(node);
    }
    return () => observer.disconnect();
  }, []);
  return current;
}

/**
 * The index: ten marks, one per chapter, that follow the reader down.
 *
 * A RAIL, NOT A ROW OF PILLS. It was a sticky horizontal strip of ten
 * rounded chips above the first chapter, which is the shape of a filter bar
 * and read as one: a reader met ten controls before a sentence. The brief is
 * specific — "a compact left index on desktop and a single 'On this page'
 * disclosure on mobile. Use a rail/list treatment, not seven rounded pills."
 *
 * So on a wide screen it is a column beside the chapters, sticky, with the
 * current chapter marked; on a phone it collapses into one line that opens.
 * Same markup, same `aria-current`, same anchors: the difference is layout
 * and a `<details>` wrapper that only does anything under the breakpoint.
 */
function useWide(query = "(min-width: 1100px)") {
  const [wide, setWide] = useState(() =>
    typeof window === "undefined" ? true : window.matchMedia(query).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setWide(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return wide;
}

function MethodsIndex() {
  const current = useCurrentChapter();
  const here = CHAPTERS.find((chapter) => chapter.id === current);
  // A closed `<details>` hides its children through the UA's own mechanism,
  // not through `display`, so no media query can open one. The breakpoint
  // has to be read in JavaScript and written to the attribute: on a wide
  // screen the rail is simply open and its cap is inert.
  const wide = useWide();
  return (
    <details className="cp-mix" aria-label="On this page" open={wide}>
      <summary className="cp-mix__cap">
        On this page
        {/* Named on a phone, where the list is closed: "On this page" alone
            says nothing about where the reader currently is. */}
        {here ? <span className="cp-mix__at">{here.label}</span> : null}
      </summary>
      <ul className="cp-mix__list">
        {CHAPTERS.map((chapter, index) => (
          <li key={chapter.id}>
            <a
              className={`cp-mix__item${current === chapter.id ? " is-on" : ""}`}
              href={`#${anchorId(chapter.id)}`}
              aria-current={current === chapter.id ? "true" : undefined}
            >
              <span className="cp-mix__ic" aria-hidden="true">{chapter.icon}</span>
              <span className="cp-mix__n" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
              <span className="cp-mix__name">{chapter.label}</span>
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}

/**
 * One chapter: its number and mark, its headline, one claim, then whatever it
 * draws. The long-form argument goes in `<Reasoning>` inside it, closed.
 */
function Chapter({ id, title, claim, children }) {
  const at = CHAPTERS.findIndex((chapter) => chapter.id === id);
  const chapter = CHAPTERS[at];
  return (
    <section className="cp-msec cp-ch cp-fade" id={anchorId(id)} aria-label={chapter.label}>
      {/* THE MARK USED TO STAND BESIDE THE WHOLE HEAD, WHICH PUSHED THE
          HEADING 60PX IN WHILE EVERY OTHER LINE IN THE SECTION -- the claim
          under it, the stage diagram, the tables -- started at the page
          gutter. A section whose own title does not share a left edge with
          its own body reads as two columns that failed to line up. The mark
          rides the numbered eyebrow instead, at eyebrow size, so the title
          and the prose sit on the same edge as everything else. */}
      <header className="cp-ch__head">
        <div className="cp-ch__id">
          <span className="cp-ch__n">
            <span className="cp-ch__mark" aria-hidden="true">{chapter.icon}</span>
            {String(at + 1).padStart(2, "0")} — {chapter.label}
          </span>
          <h2 className="cp-msec__title">{title}</h2>
        </div>
      </header>
      {claim ? <p className="cp-ch__claim">{claim}</p> : null}
      {children}
    </section>
  );
}

/**
 * The paragraph that used to sit between a headline and its diagram.
 *
 * A native disclosure: no state, keyboard and screen readers get it free, and
 * a reader who wants the argument is one click from all of it. The summary
 * says what is inside rather than "read more", so the page can be skimmed by
 * its summaries alone.
 */
// Every caller names what is inside. Review, 2026-09-15: "'The reasoning'
// is too vague for a disclosure label. Tell readers what they will find when
// they open it." The default is kept only so a future caller cannot render a
// nameless control.
function Reasoning({ label = "Why this is built this way", children }) {
  return (
    <details className="cp-why">
      <summary className="cp-why__sum">
        <span className="cp-why__cue" aria-hidden="true" />
        {label}
      </summary>
      <div className="cp-why__in">{children}</div>
    </details>
  );
}

/** A row of actions at the foot of a chapter. Never more than three. */
function Acts({ children }) {
  return <div className="cp-ch__acts">{children}</div>;
}

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
      <main id="cp-main" className="cp cp-page cp-meth" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="methods" />

        {/* THE OPENING IS TWO SENTENCES AND AN INDEX.
            Review, 2026-09-15: "the opening headline, paragraph, pull quote,
            three actions, and ten-item chapter index all precede the
            substantive explanation. On mobile, even the introduction extends
            beyond the screenshot. Shorten the title to 'How Cedar builds its
            data'. Give a brief explanation, then let readers choose a topic."
            The pull quote and the action row are gone with it.

            The claim is also narrower than it was. "Nothing in them agrees on
            who is who" is an absolute a reader can disprove with one
            counter-example; what Cedar can show is that the names and
            identifiers are inconsistent, which is the problem it solves. */}
        <section className="cp-mh cp-meth__hero">
          <h1 className="cp-mh__title">How Cedar builds its data.</h1>
          <p className="cp-mh__sub">
            Source records use inconsistent names and identifiers, so one organization appears
            under several spellings. Cedar assigns a permanent identifier to each Native
            government, enterprise and firm it can resolve, and maintains it through renames,
            acquisitions and changes in legal status.
          </p>
        </section>

        <MethodsIndex />

        <Chapter
          id="sources"
          title="Every collection runs the same seven stages."
          claim="Sources are gathered, normalized, resolved to entities and checked against each other; ambiguous matches go to a researcher rather than to a score."
        >
          <ProcessRail />
          <Reasoning label="Why the collections are built together rather than one at a time">
            <p>
              A contract award, a lobbying registration and a 990 are three records about one
              organization, and they only behave that way if the organization is identified before
              the question is asked. Selecting a collection below shows the records it is built
              from and the collections that reinforce it.
            </p>
            <EcosystemDiagram />
          </Reasoning>
          <Acts>
            <Link className="cp-ch__act" to={PRESS_DATA_PATH}>
              See what each collection holds <span aria-hidden="true">&#8594;</span>
            </Link>
          </Acts>
        </Chapter>

        {/* THE ARGUMENT THIS PAGE EXISTS FOR. The two identifiers are
            load-bearing, so they are named, shown at transcription size and
            checked against the published register by `pressIdentity.test.js`. */}
        <Chapter
          id="ids"
          title="Two identifiers: one names an entity, one names a business."
          claim="A Cedar entity id names one canonical Native entity. A Cedar business id names one distinct business or enterprise. The two namespaces never mix."
        >
          <IdentityPair />
          <Reasoning label="Why an identifier has to be minted at all">
            <p>
              A 990 says who filed it. A royalty statement says who was paid. A docket says who
              appeared. None of them says whether those three are the same nation, and no public
              system will tell you. Cedar assigns the key none of them carries and keeps it
              current. The ownership between the two namespaces is a dated relationship carrying
              its source, which is what keeps a nation and the company it owns from collapsing
              into one row.
            </p>
            <p>
              A firm that is Native-owned without being owned by a nation gets the business id
              from the first sighting. If a nation acquires it later, the history is already
              there.
            </p>
            {/* The owner's challenge, 2026-09-13: is it wrong that Cedar does
                not publish what it resolves? It would be. What is actually
                withheld is much narrower, and WITHHELD_NOTE holds the wording
                with the rule it comes from cited beside it. */}
            <p className="cp-msec__aside">{WITHHELD_NOTE}</p>
          </Reasoning>
        </Chapter>

        {/* WHY TWO NAMESPACES. The owner's worked example: one id space
            collapses an enterprise into its tribal owner, and then "what has
            this nation been involved in" and "what has this enterprise won"
            become the same query with the same wrong answer. */}
        <Chapter
          id="ownership"
          title="A nation and the company it owns are two subjects."
          claim="The ownership between them is a dated relationship carrying its source, and the identifiers themselves carry nothing that can change."
        >
          <WhyBoth />
          <h3 className="cp-ch__sub">What the identifiers deliberately do not carry</h3>
          <KeptOutside />
          <Reasoning label="What a single identifier space would cost">
            <p>
              A Native entity can own or operate a business. That does not make the business and
              the entity the same subject, and a single identifier space is a decision to treat
              them as one. An identifier that encodes ownership also has to be rewritten when a
              firm is sold, and every rewrite breaks every citation that used the old one.
            </p>
          </Reasoning>
        </Chapter>

        <Chapter
          id="linkage"
          title="What carrying an identifier makes possible, and where it stops."
          claim="Start from any keyword, agency, year or nation, and what comes back is the rows Cedar can attribute to that organization rather than the rows that happened to spell its name your way."
        >
          <LinkageMoves />
          {/* Codex, PR #77: this said the identifier "was already on every row"
              and promised the "whole footprint". LINKAGE_COVERAGE.md measures
              70.93% across the flagships and 6.24% on Natural Resource
              Revenues, so the measured figure sits under the claim, and stays
              out of the disclosure: a coverage number a reader has to open
              something to find is a number being kept quiet. */}
          <p className="cp-msec__aside">
            {LINKAGE_COVERAGE.note}
            <Explain label="how the coverage figure is counted">
              <p><span className="cp-ex1__cap">What the denominator is</span>{LINKAGE_COVERAGE.caveat}</p>
              <p><span className="cp-ex1__cap">When it was measured</span>{LINKAGE_COVERAGE.measuredOn}, against the built collections, by <code>{LINKAGE_COVERAGE.source}</code>.</p>
            </Explain>{" "}
            Measured {LINKAGE_COVERAGE.measuredOn} against the built collections.
          </p>
          {/* Two of these three are intentional and stay intentional however
              long Cedar runs: a notice addressed to every federally
              recognized tribe names no organization, and an individually
              owned firm's identity is withheld by policy. The third is work
              still to do, and it says so. Published beside the figure rather
              than behind a disclosure. */}
          <h3 className="cp-ch__sub">Why a record can carry no entity</h3>
          <UnlinkedReasons />
        </Chapter>

        <Chapter
          id="updates"
          title="Corrections go back into the evidence, and some things stay undone."
          claim="A researcher rules on every final output, and the ruling goes back into the evidence the models read."
        >
          <FeedbackLoop />
          <h3 className="cp-ch__sub">What Cedar will not do</h3>
          <ul className="cp-wont">
            {METHOD_COMMITMENTS.map((item) => (
              <li key={item.id}>{item.text}</li>
            ))}
          </ul>
          <Reasoning label="Why an identified collection answers differently">
            <p>
              A model reading twelve unjoined files can retrieve text. A model reading an
              identified collection can count, compare and trace, because the rows already agree
              on who they are about. Cedar builds and trains its own models on its own resolved
              records. The collection is the input to the next pass over it, so the specific
              questions it can answer get more specific over time.
            </p>
          </Reasoning>
          <Acts>
            <a className="cp-ch__act" href={contactHref("Cedar correction")}>
              Send a correction <span aria-hidden="true">&#8594;</span>
            </a>
          </Acts>
        </Chapter>

        {/* The philosophy above; the specifics here. A researcher's next
            question after "how does Cedar work" is "how was THIS collection
            built", and the answer is assembled from the same declarations the
            product runs on. */}
        <Chapter
          id="collections"
          title="The specifics, collection by collection."
          claim="Choose a mark for that collection's sources, method and entity resolution."
        >
          <MethodsByCollection />
        </Chapter>

        <Chapter
          id="team"
          title="Built by people who know the systems."
          claim="Cedar is built by Indigenous researchers and a team with experience at the Federal Reserve Board and the Federal Reserve Banks of Minneapolis and Philadelphia, and academic backgrounds spanning MIT, Oxford, Cornell, Brown, Dartmouth and Yale."
        >
          <div className="cp-exp">
            <div>
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
          <Acts>
            <Link className="cp-ch__act cp-ch__act--lead" to={PRESS_DATA_PATH}>
              See the collections <span aria-hidden="true">&#8594;</span>
            </Link>
            <Link className="cp-ch__act" to={PRESS_REQUEST_PATH}>
              For tribal governments: request your records <span aria-hidden="true">&#8594;</span>
            </Link>
          </Acts>
        </Chapter>

        <PressFoot />
        <PressCedarFab />
      </main>
    </div>
  );
}
