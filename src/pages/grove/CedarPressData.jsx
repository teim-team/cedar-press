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

/**
 * THE TABLE IS THE SCREEN.
 *
 * Owner, 2026-09-20: the collections page should have the table take up the
 * screen in full. That means the frame ends where the window ends, and what
 * scrolls is the records inside it — not the page, which used to carry the
 * rail and the collection's own title away with it the moment a reader
 * looked at row twenty.
 *
 * The height cannot be written in CSS alone. It is the window minus whatever
 * sits above the frame, and that is the masthead plus the title, which are
 * two different heights at two different widths and change again when the
 * nav wraps. A hardcoded `calc(100dvh - 12rem)` was wrong by 14px at 1440 and
 * by more than that on a phone. So the chrome above the frame is measured and
 * published as `--cp-frame-h`; `press.css` decides what to do with it, and a
 * width that wants a taller-than-screen frame simply ignores it.
 *
 * What is observed is the chrome, never the frame: observing the element
 * whose height this property sets would be a loop.
 */
function useFrameFill() {
  useEffect(() => {
    const main = document.getElementById("cp-main");
    if (!main) return undefined;
    let raf = 0;
    let last = "";
    const measure = () => {
      raf = 0;
      const frame = main.querySelector(".cp-ex__frame");
      if (!frame) return;
      // Document coordinates: the frame's own offset from the top of the
      // page IS the chrome above it, and unlike a viewport rect it does not
      // change as the reader scrolls.
      const top = Math.round(frame.getBoundingClientRect().top + window.scrollY);
      const next = `calc(100dvh - ${top}px - 1rem)`;
      if (next === last) return;
      last = next;
      main.style.setProperty("--cp-frame-h", next);
    };
    const schedule = () => {
      if (!raf) raf = requestAnimationFrame(measure);
    };
    schedule();
    window.addEventListener("resize", schedule);
    const chrome = [main.querySelector(".cp-mast"), main.querySelector(".cp-mh")].filter(Boolean);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(schedule);
    chrome.forEach((node) => observer?.observe(node));
    // The explorer is lazy, so the frame does not exist on the first frame.
    const settle = window.setTimeout(schedule, 400);
    return () => {
      window.removeEventListener("resize", schedule);
      observer?.disconnect();
      window.clearTimeout(settle);
      window.clearTimeout(raf);
      cancelAnimationFrame(raf);
    };
  }, []);
}

export default function CedarPressData() {
  useDocumentTitle("Collections");
  const { user, loading, logout } = useAuth();
  // Sitewide arrival language; the shelf bands keep their own reveal.
  const fadeRoot = useFadeIn();
  const { hash } = useLocation();
  const entitled = canReadCedarPress(user);
  useScrollToTop("data");
  useFrameFill();

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
