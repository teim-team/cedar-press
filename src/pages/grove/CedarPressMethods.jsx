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
  CommitmentsIcon,
  ExpertiseIcon,
  IdentityIcon,
  LinkageIcon,
  LoopIcon,
  OutsideIcon,
  ProcessIcon,
  SubjectsIcon,
  SystemIcon,
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
  { id: "process", label: "The process", icon: ProcessIcon },
  { id: "system", label: "One system", icon: SystemIcon },
  { id: "identity", label: "Identity", icon: IdentityIcon },
  { id: "subjects", label: "Two subjects", icon: SubjectsIcon },
  { id: "outside", label: "Kept outside", icon: OutsideIcon },
  { id: "linkage", label: "Linkage", icon: LinkageIcon },
  { id: "loop", label: "The loop", icon: LoopIcon },
  { id: "by-collection", label: "By collection", icon: ByCollectionIcon },
  { id: "commitments", label: "Commitments", icon: CommitmentsIcon },
  { id: "expertise", label: "Expertise", icon: ExpertiseIcon },
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

/** The index: ten marks, one per chapter, that follow the reader down. */
function MethodsIndex() {
  const current = useCurrentChapter();
  return (
    <nav className="cp-mix" aria-label="On this page">
      <span className="cp-mix__cap">On this page</span>
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
    </nav>
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
      <header className="cp-ch__head">
        <span className="cp-ch__mark" aria-hidden="true">{chapter.icon}</span>
        <div className="cp-ch__id">
          <span className="cp-ch__n">{String(at + 1).padStart(2, "0")} — {chapter.label}</span>
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
function Reasoning({ label = "The reasoning", children }) {
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

function AskCedar({ children }) {
  return (
    <button
      type="button"
      className="cp-ch__act"
      onClick={() => window.dispatchEvent(new CustomEvent("cedar:open"))}
    >
      {children} <span aria-hidden="true">&#8594;</span>
    </button>
  );
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

        {/* THE HEADLINE.
            "Public records are only the beginning" was the owner's call to
            cut, and he was right: it says the records are a starting point
            and stops, which describes a gap rather than a product, and every
            data company on earth could put it on a page. The argument is
            narrower and much harder to copy. There is no shortage of records
            about Indian Country. There is no key in any of them that says
            which organization a row belongs to, so nothing can be added up.
            Cedar mints that key and maintains it. Say that. */}
        <section className="cp-mh cp-meth__hero">
          <p className="cp-hero__access">How Cedar is built</p>
          <h1 className="cp-mh__title">The records exist. Nothing in them agrees on who is who.</h1>
          <p className="cp-mh__sub">
            Federal awards, tax filings, royalty statements, dockets, legislation and each
            nation&rsquo;s own publications hold an enormous amount about Indian Country, and no two
            of them identify an organization the same way. Cedar assigns a permanent identifier
            to every Native government, enterprise and firm it can resolve, and maintains it
            through renames, acquisitions and changes in legal status.
          </p>
          <p className="cp-mh__claim">In many cases, the collection does not exist until Cedar builds it.</p>
          {/* The three things a reader is actually here to do, at the top,
              rather than at the foot of nine arguments. */}
          <Acts>
            <Link className="cp-ch__act cp-ch__act--lead" to={PRESS_DATA_PATH}>
              See the collections <span aria-hidden="true">&#8594;</span>
            </Link>
            <AskCedar>Ask Cedar how a collection was built</AskCedar>
            <a className="cp-ch__act" href={contactHref("Cedar correction")}>
              Send a correction <span aria-hidden="true">&#8594;</span>
            </a>
          </Acts>
        </section>

        <MethodsIndex />

        <Chapter
          id="process"
          title="From scattered records to maintained intelligence."
          claim="Every Cedar collection runs the same seven stages, with collection-specific sources and resolution rules."
        >
          <ProcessRail />
          <Acts>
            <Link className="cp-ch__act" to={PRESS_DATA_PATH}>
              See what each collection holds <span aria-hidden="true">&#8594;</span>
            </Link>
          </Acts>
        </Chapter>

        <Chapter
          id="system"
          title="Built as one connected intelligence system."
          claim="Select a collection to see the records it is built from and the collections that reinforce it."
        >
          <EcosystemDiagram />
          <Reasoning label="Why the collections are built together, not one at a time">
            <p>
              The collections become more valuable because they were designed to work together.
              A contract award, a lobbying registration and a 990 are three different records
              about one organization, and they only behave that way if the organization is
              identified before the question is asked.
            </p>
          </Reasoning>
        </Chapter>

        {/* THE ARGUMENT THIS PAGE EXISTS FOR.
            Everything above says the records are gathered carefully. This says
            why the result is one collection rather than twelve datasets, and it
            is the only section whose claims a competitor would have to match
            rather than buy. The two identifiers are load-bearing, so they are
            named, shown at transcription size and checked against the published
            register by `pressIdentity.test.js`. */}
        <Chapter
          id="identity"
          title="Two identifiers, maintained by hand where it counts."
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
                not publish what it resolves? It would be. The earlier sentence
                here said the names are withheld and stopped, which described a
                product that resolves firms and then hides them. What is
                actually withheld is much narrower, and the line between the
                two cases is a judgement worth showing. WITHHELD_NOTE holds the
                wording, with the rule it comes from cited beside it. */}
            <p className="cp-msec__aside">{WITHHELD_NOTE}</p>
          </Reasoning>
        </Chapter>

        {/* WHY TWO NAMESPACES. The owner's worked example, and the argument
            the rest of the page rests on: one id space collapses an
            enterprise into its tribal owner, and then "what has this nation
            been involved in" and "what has this enterprise won" become the
            same query with the same wrong answer. */}
        <Chapter
          id="subjects"
          title="A nation and the company it owns are not one thing."
          claim="Cedar keeps two identifier spaces and puts the ownership between them, where it can carry dates and a source."
        >
          <WhyBoth />
          <Reasoning label="What a single identifier space would cost">
            <p>
              A Native entity can own or operate a business. That does not make the business and
              the entity the same subject, and a single identifier space is a decision to treat
              them as one. Collapse them and &ldquo;what has this nation been involved in&rdquo;
              and &ldquo;what has this enterprise won&rdquo; become the same query, with the same
              wrong answer.
            </p>
          </Reasoning>
        </Chapter>

        <Chapter
          id="outside"
          title="Anything that can change stays out of the identifier."
          claim="Cedar's identifiers encode nothing, so they never have to move."
        >
          <KeptOutside />
          <Reasoning label="Why an identifier that encodes facts breaks">
            <p>
              The reason a Cedar id is worth building a collection on is everything it refuses to
              hold. An identifier that encodes ownership has to be rewritten when a firm is sold;
              one that encodes a state has to be rewritten when the firm moves. Every rewrite
              breaks every citation that used the old one.
            </p>
          </Reasoning>
        </Chapter>

        <Chapter
          id="linkage"
          title="Twelve datasets stop behaving like twelve datasets."
          claim="Start from any keyword, agency, year or nation, and what comes back is the rows Cedar can attribute to that organization — not the rows that happened to spell its name your way."
        >
          <LinkageMoves />
          {/* Codex, PR #77: this said the identifier "was already on every row"
              and promised the "whole footprint". LINKAGE_COVERAGE.md measures
              70.93% across the flagships and 6.24% on Natural Resource
              Revenues, so "every row" was false and "whole footprint" would
              have a subscriber read a partial answer as a complete one. The
              measured figure sits under the claim, and stays out of the
              disclosure: a coverage number a reader has to open something to
              find is a number being kept quiet. */}
          <p className="cp-msec__aside">
            {LINKAGE_COVERAGE.note}
            <Explain label="how the coverage figure is counted">
              <p><span className="cp-ex1__cap">What the denominator is</span>{LINKAGE_COVERAGE.caveat}</p>
              <p><span className="cp-ex1__cap">When it was measured</span>{LINKAGE_COVERAGE.measuredOn}, against the built collections, by <code>{LINKAGE_COVERAGE.source}</code>.</p>
            </Explain>{" "}
            Measured {LINKAGE_COVERAGE.measuredOn} against the built collections.
          </p>
          {/* And why. Two of these three are intentional and stay intentional
              however long Cedar runs: a notice addressed to every federally
              recognized tribe names no organization, and an individually
              owned firm's identity is withheld by policy. The third is work
              still to do, and it says so. */}
          {/* Not folded. A coverage figure published beside its reasons is
              the honest form of it; the reasons behind a disclosure would be
              the figure standing alone with an explanation available on
              request. */}
          <UnlinkedReasons />
          <Reasoning label="What this buys a reader">
            <p>
              That is the difference between a shelf of files and a collection: the files hold
              records, and the collection holds an organization. An answer in one collection is a
              key into the others, so a finding can be followed rather than only reported.
            </p>
          </Reasoning>
        </Chapter>

        <Chapter
          id="loop"
          title="And the identifiers are what let Cedar answer you."
          claim="A researcher rules on every final output, and the ruling goes back into the evidence the models read."
        >
          <FeedbackLoop />
          <Reasoning label="Why an identified collection answers differently">
            <p>
              A model reading twelve unjoined files can retrieve text. A model reading an
              identified collection can count, compare and trace, because the rows already agree
              on who they are about. Cedar builds and trains its own models on its own resolved
              records. The collection is the input to the next pass over it, so the specific
              questions it can answer get more specific over time.
            </p>
          </Reasoning>
        </Chapter>

        {/* The philosophy above; the specifics here. A researcher's next
            question after "how does Cedar work" is "how was THIS collection
            built", and the answer is assembled from the same declarations the
            product runs on — the catalog, the launch descriptors and the
            release log — so a row cannot say something the collection does
            not. Ask Cedar sits on each row because the profile behind the row
            is exactly what Cedar answers from. */}
        <Chapter
          id="by-collection"
          title="The specifics, collection by collection."
          claim="Choose a mark for that collection's sources, method and entity resolution."
        >
          <MethodsByCollection />
        </Chapter>

        {/* Restraint, stated as commitments rather than left implicit: the
            things Cedar could do to look more complete and does not. */}
        <Chapter
          id="commitments"
          title="What Cedar will not do."
          claim="The things Cedar could do to look more complete, and does not."
        >
          <ul className="cp-wont">
            {METHOD_COMMITMENTS.map((item) => (
              <li key={item.id}>{item.text}</li>
            ))}
          </ul>
        </Chapter>

        <Chapter
          id="expertise"
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
            <a className="cp-ch__act cp-ch__act--lead" href={contactHref("Cedar correction")}>
              Found something wrong? Send a correction <span aria-hidden="true">&#8594;</span>
            </a>
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
