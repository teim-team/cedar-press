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

import { Link } from "react-router";
import { contactHref } from "../../features/grove/appLink.js";

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import { TRIBAL_REQUEST } from "../../features/grove/pressMethod";
import { PRESS_METHODS_PATH, PRESS_PATH } from "../../features/grove/pressRoutes";
import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";

/**
 * FOUR TASKS, FOUR DRAFTS. The brief's "short branching form": reveal only
 * what the chosen task needs, and do not open a proposal form to somebody
 * who wants to correct one relationship.
 *
 * There is no form backend on this site and inventing one would be worse, so
 * the branch is four prefilled mail drafts. Each opens on the Nation and the
 * requester's authority — the two things every route needs — and then asks
 * only what its own task needs.
 */
const AUTHORITY = [
  "NATION OR TRIBAL GOVERNMENT",
  "",
  "",
  "YOU — name, title, and your authority to act for the government",
  "",
  "",
];

const TASKS = [
  {
    id: "review",
    label: "Review the records tied to my government",
    blurb: "What Cedar Press holds about the government and its affiliated enterprises.",
    ask: ["WHAT YOU WOULD LIKE TO SEE — all records, or a collection or period"],
  },
  {
    id: "correct",
    label: "Correct an identity or an enterprise relationship",
    blurb: "A name, a classification, or a link between a government and a business.",
    ask: [
      "WHAT IS WRONG — the record, entity or relationship, and the Cedar id if you have it",
      "WHAT IS CORRECT, and what supports it",
    ],
  },
  {
    id: "missing",
    label: "Identify public records that are missing",
    blurb: "Something in the public record that Cedar Press has not picked up.",
    ask: ["WHAT IS MISSING — the source, the period, and where it is published"],
  },
  {
    id: "partner",
    label: "Discuss a data partnership",
    blurb: "Working together on data the government holds or wants built.",
    ask: ["WHAT YOU HAVE IN MIND", "TIMELINE AND WHO SHOULD BE INVOLVED"],
  },
];

const draftFor = (task) =>
  contactHref(
    `Cedar Tribal Record Review — ${task.label}`,
    [...AUTHORITY, ...task.ask.flatMap((line) => [line, "", ""])].join("\n"),
  );

const REQUEST_HREF = draftFor(TASKS[0]);

// The policy this page renders is declared once, in pressMethod.js, where
// its tests live. This file carried its own copies of every list until
// 2026-09-04, and the two had drifted: the page promised gaming operations
// and named four kinds of requester while the declaration named five.
const { included: COVERS, eligibility: REQUESTERS, verification: VERIFICATION, steps: STEPS, excluded: EXCLUDED } = TRIBAL_REQUEST;

export default function CedarPressTribalRequest() {
  useDocumentTitle("Tribal data request", {
    index: true,
    description:
      "Federally recognized tribal governments can request and review the Cedar records maintained about their nation, its enterprises and affiliated entities, and submit corrections. No subscription required.",
  });
  // Links here sit at the bottom of long pages; without the reset the
  // destination opens mid-scroll, past its headline.
  useScrollToTop();
  // A public program page: a signed-out council office gets the wordmark
  // and this page's own actions, not a section nav whose every door opens
  // onto the gate. A signed-in reader keeps the full chrome.
  const { user } = useAuth();
  const entitled = canReadCedarPress(user);
  const fadeRoot = useFadeIn();
  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast />

        <section className="cp-trh cp-fade">
          <div>
            {/* "Record review", not "data request": the page is about a
                government's right to see and correct what is held about it,
                and the old eyebrow named the audience while the new one
                names the job. And "Nation", capitalised — it is the proper
                noun for a sovereign government, and lowercase here read as
                a generic. */}
            <p className="cp-hero__access">Tribal government record review</p>
            <h1 className="cp-trh__title">See what Cedar knows about your Nation.</h1>
          </div>
          <div className="cp-trh__side">
            {/* THREE SENTENCES BECAME TWO.
                Owner, 2026-09-20: "it needs less explanation above the
                action... The dignity is right. The amount of copy is still
                too high." What a Nation may request is the next section's
                whole subject, listed there; saying it here first was the
                page explaining itself before it did anything. What stays is
                what a reader cannot learn from the section headings: that
                this is a right, and that it costs nothing. */}
            <p className="cp-trh__sub">
              Request the records Cedar maintains about your government and its enterprises,
              review them, and submit corrections.{" "}
              <b>No subscription is required.</b>
            </p>
            <a className="cp-trh__cta" href={REQUEST_HREF}>
              Request your records <span aria-hidden="true">&#8594;</span>
            </a>
          </div>
        </section>

        <section className="cp-tr2 cp-fade" aria-label="What you can request">
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
            {/* A NATION IS AUTHORITATIVE ABOUT ITSELF.
                This read "Every request is verified with the tribal
                government", which puts Cedar in the position of checking a
                government rather than checking a requester. The thing
                actually verified is that whoever is asking is authorized to
                receive the government's records, which is what the body
                below has always described — the title was the part that
                said it wrong. */}
            <h2 className="cp-verify__title">Authorized-requester confirmation.</h2>
            <p className="cp-verify__body">
              Cedar releases tribe-specific records only after confirming that the requester is
              authorized by the federally recognized tribal government.
            </p>
            {/* Seven bullets across two columns, folded. Who counts as
                authorized and what counts as confirmation are answers a
                requester needs once they are writing the request — not
                while they are deciding whether this route is theirs. */}
            <details className="cp-verify__who">
              <summary>Who may request, and what confirmation looks like</summary>
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
                  <span className="cp-verify__cap">Confirmation may include</span>
                  <ul>
                    {VERIFICATION.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </details>
            <p className="cp-verify__hard">
              Cedar does not release tribe-specific records solely because someone claims
              affiliation with the tribe.
            </p>
          </aside>
        </section>

        <section className="cp-msec cp-fade" aria-label="How it works">
          <span className="cp-sec__band">How it works</span>
          {/* Numbered like the Methods pipeline: five moments in one
              process, not five equal tiles. On phones the row becomes a
              stacked, numbered list and the eyebrow stands down — the
              sentence is the step. */}
          <ol className="cp-flow">
            {STEPS.map((item, index) => (
              <li className="cp-flow__step" key={item.step}>
                <span className="cp-flow__head">
                  <span className="cp-flow__n">{String(index + 1).padStart(2, "0")}</span>
                  <span className="cp-flow__cap">{item.step}</span>
                </span>
                <span className="cp-flow__body">{item.body}</span>
              </li>
            ))}
          </ol>
          {/* WHAT A CORRECTION CAN AND CANNOT DO.
              Owner, 2026-09-20: show "what can be requested, what cannot be
              changed casually, and why verification matters". The first and
              the third were on the page; this is the second, and it is the
              honest half — a records program that implies a government can
              edit the archive on request would be promising something Cedar
              cannot give and should not. */}
          <div className="cp-tr3">
            <p className="cp-tr3__can">
              <b>A verified correction updates what Cedar publishes next.</b> It is carried into
              the release and recorded in the change ledger, where anyone citing the old figure
              can see what moved.
            </p>
            <p className="cp-tr3__cant">
              <b>It does not alter the source record.</b> Cedar holds what an agency filed, and
              the filing stays as it was filed; a correction changes what Cedar says about it,
              beside the original. Published releases keep their addresses so a citation made
              last year still resolves.
            </p>
          </div>
        </section>

        <section className="cp-limits cp-two cp-fade" aria-label="What a request does not include">
          {/* The action moved up here from the foot of the right column. The
              left column held two lines of display type and then stopped, so
              the last thing on the page was a heading with an empty half-page
              under it; the right column carried the words AND the way out.
              The statement and the action belong together, and the section
              now ends on both columns rather than on one. */}
          <div className="cp-limits__say">
            <span className="cp-sec__band">Not included</span>
            <h2 className="cp-two__title">What a request does not cover.</h2>
            {/* The branch. Four tasks, and the draft each one opens asks only
                what that task needs — a correction should not arrive on a
                proposal form. */}
            <div className="cp-task" aria-label="Start a request">
              <span className="cp-task__cap">Start a request</span>
              <ul className="cp-task__list">
                {TASKS.map((task) => (
                  <li key={task.id}>
                    <a className="cp-task__act" href={draftFor(task)}>
                      <b>{task.label}</b>
                      <span>{task.blurb}</span>
                    </a>
                  </li>
                ))}
              </ul>
              <p className="cp-task__fine">
                Each opens a mail draft with that request&rsquo;s own questions. Nothing is sent
                until you send it.
              </p>
            </div>
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
          </div>
        </section>

        <PressFoot nav={entitled} />
        <PressCedarFab />
      </main>
    </div>
  );
}
