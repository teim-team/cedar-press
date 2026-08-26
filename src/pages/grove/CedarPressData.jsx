// Cedar Press: the data page.
//
// The shelves, behind their door on the hub. What Cedar adds leads — said
// once and up front, because without it the catalog below reads as a
// repackaging of open data, which is what a reader will assume since the
// source records genuinely are public — then the shelf itself, with the
// Cedar Grove boundary at its foot.
import "../../index.css";
import "../../styles/redesign.css";
import "../../styles/grove/press.css";
import { useEffect } from "react";
import { Link, useLocation } from "react-router";

import { useAuth } from "../../context/useAuth";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { NATIVE_LINKAGE } from "../../features/grove/pressCatalog";
import { PRESS_METHODS_PATH } from "../../features/grove/pressRoutes";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { Halo } from "./pressAtmosphere";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";
import PressShelf from "./PressShelf";

export default function CedarPressData() {
  const { user, loading, logout } = useAuth();
  const { hash } = useLocation();
  const entitled = canReadCedarPress(user);
  useScrollToTop("data");

  // Arriving with a fragment (an article's "Make your own" lands on
  // /data#grove) scrolls to that section once it exists. Client routing
  // does not do this on its own, and the target is rendered by a child on a
  // later frame than this one, hence the deferral.
  useEffect(() => {
    if (!hash) return;
    const frame = requestAnimationFrame(() => {
      document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
    });
    return () => cancelAnimationFrame(frame);
  }, [hash]);

  if (!loading && !entitled) {
    return (
      <div className="teim-rd teim-rd--paper">
        <PressGate user={user} />
      </div>
    );
  }
  return (
    <div className="teim-rd teim-rd--paper">
      <div className="cp">
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="data" />

        <section className="cp-mh">
          <p className="cp-hero__access">The collections</p>
          <h1 className="cp-mh__title">Every collection, and what it holds.</h1>
          <p className="cp-mh__sub">
            Each collection is assembled from records that were never designed to work
            together, resolved to the Native entities behind them and maintained as new
            material arrives. Open one to see its coverage and method; the release comes
            down with it.
          </p>
        </section>

        {/* The differentiator, said once and up front. The tiers are listed
            because "Native" covers several distinct relationships and
            merging them would be a claim the data does not support. */}
        <section className="cp-surf cp-surf--pale cp-link" aria-label="What Cedar adds">
          <Halo strength={0.8} />
          <div className="cp-surf__in">
            <div className="cp-head">
              <span className="cp-sec__band">What Cedar adds</span>
              <span className="cp-kind cp-kind--data">About the collections</span>
            </div>
            <div className="cp-link__in">
              <h2 className="cp-link__claim">{NATIVE_LINKAGE.claim}</h2>
              <p className="cp-link__body">{NATIVE_LINKAGE.body}</p>
            </div>
            <p className="cp-link__hard">{NATIVE_LINKAGE.hard}</p>
            <ul className="cp-link__tiers">
              {NATIVE_LINKAGE.groups.map((group) => (
                <li key={group}>{group}</li>
              ))}
            </ul>
            <p>
              <Link className="cp-m__more" to={PRESS_METHODS_PATH}>
                See Cedar&rsquo;s entity methodology <span aria-hidden="true">&#8594;</span>
              </Link>
            </p>
          </div>
        </section>

        <PressShelf user={user} />

        <PressCedarFab />
        <PressFoot />
      </div>
    </div>
  );
}
