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

import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";
import { Link } from "react-router";

import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import { PRESS_PATH, PRESS_REQUEST_PATH } from "../../features/grove/pressRoutes";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import {
  CREDIBILITY_DISCLAIMER,
  CREDIBILITY_STRIP,
} from "../../features/grove/pressMethod";
import { EcosystemDiagram, ProcessRail, EntityTimeline } from "./pressMethodSections";
import { PressCedarFab } from "./PressCedarFab";


const TRUST_ROW = [
  "Documented methodology",
  "Versioned releases",
  "Human review",
  "Source register",
  "Correction process",
];

export default function CedarPressMethods() {
  useScrollToTop();
  return (
    <div className="teim-rd teim-rd--paper">
      <div className="cp">
        <header className="cp-mast">
          <Link className="cp-mast__word" to={PRESS_PATH}>
            CEDAR PRESS
          </Link>
          <span className="cp-mast__of">Methods</span>
        </header>

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

        <p className="cp-mh__claim">In many cases, the collection does not exist until Cedar builds it.</p>

        <section className="cp-msec" aria-label="The process">
          <span className="cp-sec__band">The process</span>
          <h2 className="cp-msec__title">From scattered records to maintained intelligence.</h2>
          <ProcessRail />
        </section>

        <section className="cp-msec" aria-label="One connected system">
          <span className="cp-sec__band">One system</span>
          <h2 className="cp-msec__title">Built as one connected intelligence system.</h2>
          <EcosystemDiagram />
          <p className="cp-msec__close">
            The collections become more valuable because they were designed to work together.
          </p>
        </section>

        <section className="cp-msec" aria-label="Maintenance">
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

        <section className="cp-msec" aria-label="Expertise and accountability">
          <span className="cp-sec__band">Expertise</span>
          <h2 className="cp-msec__title">Built by people who know the systems.</h2>
          <div className="cp-exp">
            <div>
              <p className="cp-msec__lede">
                Cedar is built by Indigenous researchers and a team with experience at the Federal
                Reserve Board and Federal Reserve Bank of Minneapolis, academic backgrounds
                spanning MIT, Oxford, Cornell, Brown, Dartmouth and Yale, and decades of combined
                work in Indian Country.
              </p>
              <p className="cp-exp__body">
                Federal funding, contracting, gaming, natural resources, policy and Native
                institutions each have different definitions, reporting systems and historical
                quirks. Reliable data requires knowing how to process the records and what those
                records mean.
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
            <a className="cp-m__more" href="mailto:contact@lumecon.ai?subject=Cedar%20correction">
              Found something wrong? Send a correction <span aria-hidden="true">&#8594;</span>
            </a>
          </p>
        </section>

        <footer className="cp-foot">
          <span>
            <Link to={PRESS_PATH}>Cedar Press</Link>
            {" · "}
            <Link to={PRESS_REQUEST_PATH}>Tribal data request</Link>
          </span>
          <span>
            <a href={TBN_URL} target="_blank" rel="noreferrer">tribalbusinessnews.com</a>
            {" · "}
            <a href={LUMECON_URL} target="_blank" rel="noreferrer">lumecon.ai</a>
          </span>
          <span>Every collection carries its method · corrections reach every release they touch</span>
        </footer>
        <PressCedarFab />
      </div>
    </div>
  );
}
