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

const REQUEST_HREF =
  contactHref("Cedar Limited Research Data Request");

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
        <PressMast nav={entitled} user={entitled ? user : null} />

        <section className="cp-trh">
          <div>
            <p className="cp-hero__access">Limited research access</p>
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

        <p className="cp-mh__claim">Two-page proposal maximum.</p>

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

        <section className="cp-msec cp-fade" aria-label="What to include">
          <span className="cp-sec__band">Include in the proposal</span>
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
          <a className="cp-trh__cta" href={REQUEST_HREF}>
            Submit a research request <span aria-hidden="true">&#8594;</span>
          </a>
        </section>

        <PressFoot nav={entitled} />
        <PressCedarFab />
      </main>
    </div>
  );
}
