// REVIEW OWNER: Havala
//
// Tribal data request: obtain and validate your government's records.
//
// One job. The previous version was four columns of bullets that read as terms
// and conditions, which is the wrong register for a page a council office is
// meant to act on. A reader should understand the policy in under a minute and
// know exactly what to send.
//
// The scope is deliberately narrow and stated plainly: federally recognized
// tribal governments. ANCs, NHOs, nonprofits and advocacy organizations are
// not covered by default, because a program that releases tribe-specific
// records on a claim of affiliation is not a program anyone should trust.

import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";
import { Link } from "react-router";

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import { PRESS_METHODS_PATH, PRESS_PATH } from "../../features/grove/pressRoutes";
import { PressCedarFab } from "./PressCedarFab";
import { useScrollToTop } from "../../features/grove/useScrollToTop";

const REQUEST_HREF =
  "mailto:contact@lumecon.ai?subject=Cedar%20Tribal%20Data%20Request";

const COVERS = [
  "Tribal government records",
  "Affiliated tribal enterprises",
  "Gaming operations",
  "Wholly owned or controlled entities",
  "Other records Cedar can reliably associate with the requesting tribal government",
];

const REQUESTERS = [
  "An elected tribal official",
  "An authorized tribal employee",
  "Tribal legal counsel",
  "A formally designated representative",
];

const VERIFICATION = [
  "An official tribal-government email address",
  "A signed authorization",
  "Confirmation from leadership, the executive office or legal counsel",
];

const STEPS = [
  { step: "Request", body: "Request your records" },
  { step: "Verify", body: "Confirm governmental authority" },
  { step: "Deliver", body: "Receive the tribe-specific package" },
  { step: "Review", body: "Review Cedar's records" },
  { step: "Correct", body: "Submit documentation or corrections" },
];

// Written in the case they are read in. Lowercasing these in the component
// turned "Cedar" into "cedar" halfway down the sentence.
const EXCLUDED = [
  "other tribes' records",
  "national comparative collections",
  "proprietary crosswalks",
  "Cedar's internal matching systems",
  "the complete Cedar entity graph",
  "restricted third-party information",
];

export default function CedarPressTribalRequest() {
  // Links here sit at the bottom of long pages; without the reset the
  // destination opens mid-scroll, past its headline.
  useScrollToTop();
  return (
    <div className="teim-rd teim-rd--paper">
      <div className="cp">
        <header className="cp-mast">
          <Link className="cp-mast__word" to={PRESS_PATH}>
            CEDAR PRESS
          </Link>
          <span className="cp-mast__of">Tribal data request</span>
        </header>

        <section className="cp-trh">
          <div>
            <p className="cp-hero__access">For federally recognized tribal governments</p>
            <h1 className="cp-trh__title">See what Cedar knows about your nation.</h1>
          </div>
          <div className="cp-trh__side">
            <p className="cp-trh__sub">
              Federally recognized tribal governments may request the Cedar records maintained
              about their government and affiliated tribal enterprises, review those records and
              submit corrections or supporting documentation.
            </p>
            <a className="cp-trh__cta" href={REQUEST_HREF}>
              Request your records <span aria-hidden="true">&#8594;</span>
            </a>
          </div>
        </section>

        <section className="cp-tr2" aria-label="What you can request">
          <div>
            <span className="cp-sec__band">What you can request</span>
            <ul className="cp-tr2__list">
              {COVERS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          {/* The one tinted panel on the page. Verification is the part that
              makes the program safe to run, so it gets the emphasis rather
              than being a fourth column of bullets. */}
          <aside className="cp-verify">
            <h2 className="cp-verify__title">Every request is verified with the tribal government.</h2>
            <p className="cp-verify__body">
              Cedar releases tribe-specific records only after confirming that the requester is
              authorized by the federally recognized tribal government.
            </p>
            <div className="cp-verify__cols">
              <div>
                <span className="cp-verify__cap">Who may request</span>
                <ul>
                  {REQUESTERS.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <span className="cp-verify__cap">Verification may include</span>
                <ul>
                  {VERIFICATION.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
            <p className="cp-verify__hard">
              Cedar does not release tribe-specific records solely because someone claims
              affiliation with the tribe.
            </p>
          </aside>
        </section>

        <section className="cp-msec" aria-label="How it works">
          <span className="cp-sec__band">How it works</span>
          <ol className="cp-flow">
            {STEPS.map((item) => (
              <li className="cp-flow__step" key={item.step}>
                <span className="cp-flow__cap">{item.step}</span>
                <span className="cp-flow__body">{item.body}</span>
              </li>
            ))}
          </ol>
          <p className="cp-msec__close">
            Verified corrections can improve future Cedar releases.
          </p>
        </section>

        <section className="cp-limits cp-two" aria-label="What a request does not include">
          <div>
            <span className="cp-sec__band">Not included</span>
            <h2 className="cp-two__title">What a request does not cover.</h2>
          </div>
          <div>
          <p className="cp-limits__body">
            A tribal data request does not include{" "}
            {EXCLUDED.map((item, i) => (
              <span key={item}>
                <b>{item}</b>
                {i < EXCLUDED.length - 2 ? ", " : i === EXCLUDED.length - 2 ? " or " : "."}
              </span>
            ))}
          </p>
          <p className="cp-limits__scope">
            This program is for federally recognized tribal governments. Alaska Native
            Corporations, Native Hawaiian Organizations, Native nonprofits and advocacy
            organizations are covered only where a request is properly authorized by a federally
            recognized tribal government concerning an entity it owns or controls.
          </p>
          <a className="cp-trh__cta" href={REQUEST_HREF}>
            Request your records <span aria-hidden="true">&#8594;</span>
          </a>
          </div>
        </section>

        <footer className="cp-foot">
          <span>
            <Link to={PRESS_PATH}>Cedar Press</Link>
            {" · "}
            <Link to={PRESS_METHODS_PATH}>Methods</Link>
          </span>
          <span>
            <a href={TBN_URL} target="_blank" rel="noreferrer">tribalbusinessnews.com</a>
            {" · "}
            <a href={LUMECON_URL} target="_blank" rel="noreferrer">lumecon.ai</a>
          </span>
          <span>Requests are verified with the tribal government before any records are released</span>
        </footer>
        <PressCedarFab />
      </div>
    </div>
  );
}
