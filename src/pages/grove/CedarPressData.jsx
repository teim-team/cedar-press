// Cedar Press: the data page.
//
// The shelves, behind their door on the hub: the headline, then the shelf
// itself, with the Cedar Grove boundary at its foot. The "what Cedar adds"
// band that used to stand between the two is now the single link under the
// headline — the argument is Methods's job, and repeating it here delayed
// the collections a reader opened this page for.
import { useEffect } from "react";
import { useLocation } from "react-router";

import { useAuth } from "../../context/useAuth";
import { useFadeIn } from "../../features/grove/useFadeIn";
import { canReadCedarPress } from "../../features/grove/pressAccess";
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
      <main id="cp-main" className="cp cp-page cp-page--table" ref={fadeRoot}>
        <PressMast user={entitled ? user : null} onSignOut={() => logout()} section="data" />

        {/* COLLECTIONS, THEN THE COLLECTIONS.
            Review, 2026-09-15: "the remaining introduction still consumes
            almost the entire mobile screen. Replace 'Every collection, and
            what it holds' with simply 'Collections'. Remove the paragraph
            about records never being designed to work together. That belongs
            in Methods. Move the entity-methodology link into collection
            information or the footer. Understanding entity resolution should
            not be a prerequisite for choosing Federal Funding."
            All three. The methodology link is in the footer, which every page
            carries, and in each collection's own panel, where a reader asking
            how this collection was built is already looking. */}
        <section className="cp-mh cp-fade">
          <h1 className="cp-mh__title">Collections</h1>
        </section>

        <PressShelf user={user} />

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
