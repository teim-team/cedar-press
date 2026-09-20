// Cedar Press: the table-first collections page.
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
  const { user, loading } = useAuth();
  // Sitewide arrival language.
  const fadeRoot = useFadeIn();
  const { hash } = useLocation();
  const entitled = canReadCedarPress(user);
  useScrollToTop("data");
  useFrameFill();

  // Preserve the article deep link to the compact Cedar Grove handoff below
  // the lazy-loaded collection frame. The table can change height as its
  // preview arrives, so retry briefly after the target mounts rather than
  // scrolling once into an unfinished layout.
  useEffect(() => {
    if (!hash) return;
    let id = hash.slice(1);
    try { id = decodeURIComponent(id); } catch { /* An invalid fragment simply has no target. */ }
    let finished = false;
    let fallback = 0;
    const root = document.getElementById("cp-main");
    const observer = new MutationObserver(() => { scrollToTarget(); });
    const stop = () => {
      observer.disconnect();
      window.clearTimeout(fallback);
    };
    const scrollToTarget = (force = false) => {
      if (finished) return true;
      const target = document.getElementById(id);
      if (!target) return false;
      // `#grove` is mounted before the lazy collection frame has real
      // height. Wait for its first useful content so the one anchor scroll
      // lands on the handoff, then leave a reader in control of the page.
      const ready = document.getElementById("cp-main")?.querySelector(".cp-ex__table tbody tr, .cp-ex__cardbtn, [data-testid='explore-unavailable']");
      if (!ready && !force) return false;
      target.scrollIntoView({ behavior: "auto", block: "start" });
      finished = true;
      stop();
      return true;
    };
    observer.observe(root ?? document.body, { childList: true, subtree: true });
    scrollToTarget();
    if (!finished) fallback = window.setTimeout(() => { scrollToTarget(true); }, 2_000);
    return () => {
      stop();
    };
  }, [hash, loading, entitled]);

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
        <PressMast section="data" />

        <PressShelf user={user} />

        <PressCedarFab />
        <PressFoot />
      </main>
    </div>
  );
}
