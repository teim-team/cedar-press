// REVIEW OWNER: Havala
//
// Limited research access: request one or two collections for a narrow project.
//
// Deliberately not another subscription page. The job is to make the fit
// obvious and the ask small, so a researcher who belongs here sends a
// two-page proposal and a research programme that does not belong here
// recognises itself and goes to Cedar Press+ or Cedar Grove instead.

import { Link } from "react-router";
import { contactHref } from "../../features/grove/appLink.js";

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import { PRESS_METHODS_PATH, PRESS_PATH } from "../../features/grove/pressRoutes";
import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";

/**
 * The proposal, as a draft rather than as a checklist the reader retypes.
 *
 * The brief asks this page to begin with "What are you trying to answer?"
 * and it now does, in the place it matters: the draft opens on the research
 * question, and the background the old list started with (title,
 * affiliation) comes after it. A request shaped this way can be read in one
 * pass; the same request as a paragraph has to be taken apart first.
 */
const DRAFT = [
  "WHAT ARE YOU TRYING TO ANSWER?",
  "",
  "",
  "WHICH ONE OR TWO COLLECTIONS, AND WHY THOSE",
  "",
  "",
  "SCOPE — dates, geography or entities",
  "",
  "",
  "WHAT YOU INTEND TO PUBLISH",
  "",
  "",
  "TIMELINE",
  "",
  "",
  "YOU — name, affiliation, contact",
  "",
  "",
].join("\n");

const REQUEST_HREF = contactHref("Cedar Limited Research Data Request", DRAFT);

const PROPOSAL = [
  "Project title",
  "Research question",
  "One or two requested Cedar collections",
  "Why those collections are needed",
  "Affiliation",
  "Expected output",
  "Project timeline",
];

export default function CedarPressResearchAccess() {
  useDocumentTitle("Research access", {
    index: true,
    description:
      "Limited research access to one or two Cedar Press collections for a defined project: for researchers, journalists, students, nonprofits and public-interest work on tribal governments, Native enterprises and Indian Country's economy.",
  });
  // Links here sit at the bottom of long pages; without the reset the
  // destination opens mid-scroll, past its headline.
  useScrollToTop();
  // A public program page: signed out, the section nav's every door opens
  // onto the gate, so only the wordmark leads out. Signed in, full chrome.
  const { user } = useAuth();
  const entitled = canReadCedarPress(user);
  const fadeRoot = useFadeIn();
  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast />

        <section className="cp-trh cp-fade">
          <div>
            {/* "Project-specific" rather than "limited": the limit is the
                point of the route, and naming it as a restriction invites
                the reading that this is a lesser subscription. */}
            <p className="cp-hero__access">Project-specific research access</p>
            <h1 className="cp-trh__title">
              Need one or two Cedar collections for a defined project?
            </h1>
          </div>
          <div className="cp-trh__side">
            <p className="cp-trh__sub">
              Researchers, journalists, students, nonprofits and public-interest organizations may
              request limited project-specific access when a full Cedar subscription does not fit
              the scope of the work.
            </p>
            <a className="cp-trh__cta" href={REQUEST_HREF}>
              Submit a research request <span aria-hidden="true">&#8594;</span>
            </a>
          </div>
        </section>

        {/* "TWO-PAGE PROPOSAL MAXIMUM." WAS A BILLBOARD.
            Owner, 2026-09-20: this route "should feel like a concise
            project-intake route: one clear request, one explanation of what
            happens next, one compact scope checklist." A page-wide teal
            claim announcing a length limit is not any of those three — it is
            a rule about the form, at the size of a headline. It is a line in
            the checklist's own heading now, where somebody writing the thing
            will read it. */}

        {/* Fit, as one comparison rather than a page of criteria. The two
            examples do more work than a policy paragraph would. */}
        <section className="cp-fit cp-fade" aria-label="Whether this fits">
          <div className="cp-fit__side cp-fit__side--yes">
            <span className="cp-fit__cap">Good fit</span>
            <p>A researcher needs the Advocacy collection for one defined journal article.</p>
          </div>
          <div className="cp-fit__side cp-fit__side--no">
            <span className="cp-fit__cap">Not a fit</span>
            <p>A research program wants six Cedar collections for open-ended analysis.</p>
          </div>
        </section>

        {/* The seven proposal items are instructions for someone who has
            already decided to apply; open by default they sat between the
            fit examples and the action, so a reader deciding whether this is
            for them had to scroll a checklist to reach the button. */}
        <details className="cp-msec cp-prop__wrap cp-fade" aria-label="What to include" open>
          <summary className="cp-prop__sum">
            <span className="cp-sec__band">Include in the proposal</span>
            <span className="cp-prop__max">Two pages maximum</span>
          </summary>
          <ol className="cp-prop">
            {PROPOSAL.map((item, i) => (
              <li key={item}>
                <span className="cp-prop__n">{String(i + 1).padStart(2, "0")}</span>
                <span>{item}</span>
              </li>
            ))}
          </ol>
          <p className="cp-msec__close cp-prop__policy">
            Access is project-specific and discretionary. Raw collections may not be
            redistributed. Projects requiring broad, repeated, exploratory or commercial access
            should use Cedar Press<span className="cp-plus">+</span> or Cedar Grove.
          </p>
          {/* "WHAT THIS ROUTE IS NOT" IS GONE, AND SAID TWICE BEFORE IT.
              Four bullets — every collection, open-ended research,
              confidential data, commercial repackaging — each of which the
              "not a fit" example above and the discretionary sentence beside
              it already carry. The review's word for this page was that it
              "repeats the same pitch"; this was the repetition. */}
          {/* WHAT HAPPENS NEXT, which the page never said. */}
          <ol className="cp-next">
            <li><b>A person reads it.</b> Requests go to the research desk, not to a queue.</li>
            <li><b>A fit gets the named collections, for the named project.</b> Nothing wider.</li>
            <li><b>A miss gets an answer anyway</b> — which route fits, if one does.</li>
          </ol>
          <a className="cp-trh__cta" href={REQUEST_HREF}>
            Start a research request <span aria-hidden="true">&#8594;</span>
          </a>
          <p className="cp-prop__fine">
            Opens a mail draft with these questions in order. Nothing is sent until you send it.
          </p>
        </details>

        <PressFoot nav={entitled} />
        <PressCedarFab />
      </main>
    </div>
  );
}
