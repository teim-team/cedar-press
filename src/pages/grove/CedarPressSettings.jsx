// Settings: the account, and the pages that were crowding the footer.
//
// The footer had grown to eight links because every page it could reach was
// listed in it. The three that are errands rather than reading — the tribal
// data request, research access, and contact — live here now, with the
// account, so the footer can go back to being a footer.
//
// Nothing on this page asks the subscriber to describe themselves. The
// account exists because a subscription does; what the service knows about
// a reader is what the subscription already carries.
import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";
import { Link } from "react-router";

import { useAuth } from "../../context/useAuth";
import { isConnected } from "../../config.js";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { LUMECON_URL, TBN_URL } from "../../features/grove/pressArticles";
import { PRESS_TIERS } from "../../features/grove/pressCatalog";
import { PRESS_REQUEST_PATH, PRESS_RESEARCH_PATH } from "../../features/grove/pressRoutes";
import { resolveTier } from "../../workspaceTier.js";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";
import { TierName } from "./TierName";

export default function CedarPressSettings() {
  useDocumentTitle("Settings");
  const { user, loading, logout } = useAuth();
  const entitled = canReadCedarPress(user);
  useScrollToTop("settings");

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
      <main className="cp">
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} />

        <section className="cp-mh">
          <p className="cp-hero__access">Settings</p>
          <h1 className="cp-mh__title">Your account.</h1>
          <p className="cp-mh__sub">
            Cedar Press accounts come with a Tribal Business News subscription. Membership,
            billing and renewals are handled there; what this page holds is what the account
            reaches from here.
          </p>
        </section>

        <div className="cp-set">
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
                href={`${TBN_URL}/cedar-press`}
                target="_blank"
                rel="noreferrer"
              >
                Manage membership <span aria-hidden="true">&#8594;</span>
              </a>
              <button type="button" className="gv-btn gv-btn--quiet" onClick={() => logout()}>
                Sign out
              </button>
            </div>
            {isConnected() ? null : (
              <p className="cp-set__fine">
                This deployment is not connected to the platform, so the session is local to this
                browser.
              </p>
            )}
          </section>

          <section className="cp-set__card" aria-label="Requests">
            <span className="cp-set__cap">Requests</span>
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
