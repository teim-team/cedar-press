// Settings: the account, the errands, and one optional question.
//
// The footer had grown to eight links because every page it could reach was
// listed in it. The three that are errands rather than reading — the tribal
// data request, research access, and contact — live here now, with the
// account, so the footer can go back to being a footer.
//
// Nothing here is required to read anything. The one question this page
// asks is asked plainly: more detail means better-curated collections, and
// a reader who does not want to answer never sees it again.
import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { usePriorities } from "../../features/grove/usePriorities.js";
import { PressInfluence } from "./PressInfluence";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { WORK_KINDS, loadWork, saveWork } from "../../features/grove/readerWork.js";
import { LUMECON_URL, TBN_PLANS_URL, TBN_URL } from "../../features/grove/pressArticles";
import { PRESS_TIERS } from "../../features/grove/pressCatalog";
import { PRESS_REQUEST_PATH, PRESS_RESEARCH_PATH } from "../../features/grove/pressRoutes";
import { resolveTier } from "../../workspaceTier.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";
import { TierName } from "./TierName";

/**
 * The one question. Optional, remembered, and stated as the trade it is:
 * telling the desk what you work on is how the collections get built for
 * the people reading them.
 */
function WorkCard() {
  const [work, setWork] = useState("");
  const [saved, setSaved] = useState(null);
  const [busy, setBusy] = useState(false);

  const apply = useCallback((value) => {
    setSaved(value);
    setWork(value ?? "");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let live = true;
    (async () => {
      const value = await loadWork({ signal: controller.signal }).catch(() => null);
      if (live) apply(value);
    })();
    return () => {
      live = false;
      controller.abort();
    };
  }, [apply]);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      apply(await saveWork(work));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="cp-set__card" aria-label="What you work on">
      <span className="cp-set__cap">What you work on</span>
      <p className="cp-set__body">
        Give us more detail and we curate the collections better: what you work on decides
        which get extended, which get a brief, and whose requests carry weight.
      </p>
      <form className="cp-set__form" onSubmit={submit}>
        <label className="cp-who__label" htmlFor="cp-work">
          Your work
        </label>
        <select id="cp-work" value={work} onChange={(event) => setWork(event.target.value)}>
          <option value="">Rather not say</option>
          {WORK_KINDS.map((kind) => (
            <option key={kind.id} value={kind.id}>
              {kind.label}
            </option>
          ))}
        </select>
        <div className="cp-set__acts">
          <button type="submit" className="gv-btn gv-btn--quiet" disabled={busy || work === (saved ?? "")}>
            {busy ? "Saving" : saved ? "Update" : "Save"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default function CedarPressSettings() {
  useDocumentTitle("Settings");
  const { user, loading, logout } = useAuth();
  const entitled = canReadCedarPress(user);
  useScrollToTop("settings");
  // Sitewide arrival language.
  const fadeRoot = useFadeIn();
  const { influence, status: influenceStatus } = usePriorities({ signedIn: entitled });

  if (!loading && !entitled) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }

  const tierId = resolveTier(user);
  const tier = PRESS_TIERS.find((entry) => entry.id === tierId);

  return (
    <div className="teim-rd teim-rd--paper">
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} />

        <section className="cp-mh cp-fade">
          <p className="cp-hero__access">Settings</p>
          <h1 className="cp-mh__title">Your account.</h1>
          <p className="cp-mh__sub">
            Cedar Press access is provided through a Tribal Business News subscription.
            Membership, billing and renewals are managed there. This page shows your Cedar
            Press access and preferences.
          </p>
        </section>

        <div className="cp-set cp-fade">
          <section className="cp-set__card" aria-label="Subscription">
            <span className="cp-set__cap">Subscription</span>
            <dl className="cp-set__rows">
              <div>
                <dt>Signed in as</dt>
                <dd>{user?.email}</dd>
              </div>
              <div>
                <dt>Plan</dt>
                <dd>{tier ? <TierName name={tier.name} /> : "Cedar Press"}</dd>
              </div>
              <div>
                <dt>Sold and renewed by</dt>
                <dd>
                  <a href={TBN_URL} target="_blank" rel="noreferrer">Tribal Business News</a>
                </dd>
              </div>
            </dl>
            <div className="cp-set__acts">
              <a
                className="gv-btn gv-btn--primary"
                href={TBN_PLANS_URL}
                target="_blank"
                rel="noreferrer"
              >
                Manage TBN membership <span aria-hidden="true">&#8594;</span>
              </a>
              <button type="button" className="gv-btn gv-btn--quiet" onClick={() => logout()}>
                Sign out
              </button>
            </div>
          </section>

          {/* Where the account's influence lives: what this subscription has
              earned by using the product, where it put it, and what it asked
              for. The page is worth visiting for this, not only for billing. */}
          <PressInfluence influence={influence} tier={tierId} status={influenceStatus} />

          <WorkCard />

          {/* Links out to public programs, not features of the account: both
              pages work with or without a subscription, and the gate and
              footer name them to non-subscribers too. This card is the
              signed-in convenience. */}
          <section className="cp-set__card" aria-label="Requests and support">
            <span className="cp-set__cap">Requests &amp; support</span>
            <ul className="cp-set__links">
              <li>
                <Link to={PRESS_REQUEST_PATH}>
                  <b>Tribal data request</b>
                  <span>
                    What Cedar holds about a nation, and how a government asks for it or asks it
                    to be corrected.
                  </span>
                </Link>
              </li>
              <li>
                <Link to={PRESS_RESEARCH_PATH}>
                  <b>Research access</b>
                  <span>
                    One or two collections for a defined project, for work that does not warrant a
                    subscription.
                  </span>
                </Link>
              </li>
              <li>
                <a href="mailto:contact@lumecon.ai?subject=Cedar%20Press">
                  <b>Contact the research desk</b>
                  <span>
                    Corrections, questions about a method, and what the collections should cover
                    next.
                  </span>
                </a>
              </li>
            </ul>
          </section>

          <section className="cp-set__card" aria-label="The platform">
            <span className="cp-set__cap">Beyond Cedar Press</span>
            <p className="cp-set__body">
              Cedar Grove carries the same collections into the environment they were built for:
              record-level exploration, entity filters, full histories and Cedar across all of
              them at once.
            </p>
            <a className="gv-btn gv-btn--quiet" href={LUMECON_URL} target="_blank" rel="noreferrer">
              About Cedar Grove <span aria-hidden="true">&#8594;</span>
            </a>
          </section>
        </div>

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
