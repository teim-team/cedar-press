// Cedar Press: the data page.
//
// The shelves, behind their door on the hub: the headline, then the shelf
// itself, with the Cedar Grove boundary at its foot. The "what Cedar adds"
// band that used to stand between the two is now the single link under the
// headline — the argument is Methods's job, and repeating it here delayed
// the collections a reader opened this page for.
import { useEffect } from "react";
import { Link, useLocation } from "react-router";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { canReadCedarPress } from "../../features/grove/pressAccess";
import { PRESS_METHODS_PATH } from "../../features/grove/pressRoutes";
import { useDocumentTitle } from "../../features/grove/useDocumentTitle";
import { useScrollToTop } from "../../features/grove/useScrollToTop";
import { PressCedarFab } from "./PressCedarFab";
import { PressFoot, PressMast } from "./PressChrome";
import PressGate from "./PressGate";
import PressShelf from "./PressShelf";

export default function CedarPressData() {
  useDocumentTitle("Collections");
  const { user, loading, logout } = useAuth();
  // Sitewide arrival language; the shelf bands keep their own reveal.
  const fadeRoot = useFadeIn();
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
      <main id="cp-main" className="cp cp-page" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="data" />

        <section className="cp-mh cp-fade">
          <p className="cp-hero__access">The collections</p>
          <h1 className="cp-mh__title">Every collection, and what it holds.</h1>
          <p className="cp-mh__sub">
            Each collection is assembled from records that were never designed to work
            together, resolved to the Native entities behind them and maintained as new
            material arrives. Open one to see its coverage and method; the release comes
            down with it.
          </p>
          {/* The differentiator used to be a full band here — a claim, a
              paragraph, a hard line and four group chips — above the shelf
              the reader came for. The owner's note, 2026-09-14: it is the
              same argument Methods makes at length, and standing between the
              headline and the collections it read as a second headline. It is
              one link now, where a reader who wants the argument will look
              for it. */}
          <p className="cp-mh__act">
            <Link className="cp-m__more" to={PRESS_METHODS_PATH}>
              How Cedar resolves a record to a Native entity <span aria-hidden="true">&#8594;</span>
            </Link>
          </p>
        </section>

        <PressShelf user={user} />

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
