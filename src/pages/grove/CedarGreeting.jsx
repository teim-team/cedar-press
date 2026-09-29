import { useCallback, useEffect, useState } from "react";

/**
 * THE GREETING NOTE ABOVE ASK CEDAR (owner, 2026-09-27).
 *
 * A short note that rises above the launcher once a reader has scrolled
 * into the page, the way IMPLAN's does and the way lumecon.ai's now does
 * (CedarFAB.astro there): a third of a screen, or the page's whole scroll
 * when it is shorter than that, and never in the first moment after load.
 * It stays until it is answered. Dismissing it or opening Cedar holds for
 * the rest of the visit; merely scrolling past it does not, so it greets
 * again on the next page. No emoji.
 *
 * It sits in the launcher's own column (both `.cp-dc` and `.cedar-widget`
 * stack their children above the button), so it follows the launcher into
 * whatever corner the page puts it, and the stylesheet hides it wherever it
 * hides the launcher.
 */

export const GREETING_KEY = "cedar-press-greeting-dismissed";
export const GREETING_DELAY_MS = 1500;

function dismissedThisVisit() {
  try {
    return window.sessionStorage.getItem(GREETING_KEY) === "1";
  } catch {
    return false;
  }
}

function markGreetingDone() {
  try {
    window.sessionStorage.setItem(GREETING_KEY, "1");
  } catch {
    // Storage unavailable: dismissing still hides it on this page.
  }
}

/** How far a reader has to scroll before the note rises. */
function greetingThreshold(viewportHeight, scrollRoom) {
  return Math.min(viewportHeight / 3, Math.max(scrollRoom - 4, 0));
}

export function CedarGreeting({ cedarOpen, onOpen }) {
  const [shown, setShown] = useState(false);
  const [done, setDone] = useState(() => typeof window !== "undefined" && dismissedThisVisit());

  useEffect(() => {
    if (done || shown || typeof window === "undefined") return undefined;
    const loadedAt = Date.now();
    let timer = 0;
    const check = () => {
      const root = document.documentElement;
      const need = greetingThreshold(window.innerHeight, root.scrollHeight - window.innerHeight);
      if (window.scrollY < need) return;
      const wait = GREETING_DELAY_MS - (Date.now() - loadedAt);
      if (wait > 0) {
        window.clearTimeout(timer);
        timer = window.setTimeout(check, wait);
        return;
      }
      setShown(true);
    };
    window.addEventListener("scroll", check, { passive: true });
    window.addEventListener("resize", check, { passive: true });
    // A page with nothing to scroll still gets its greeting.
    timer = window.setTimeout(check, GREETING_DELAY_MS);
    return () => {
      window.removeEventListener("scroll", check);
      window.removeEventListener("resize", check);
      window.clearTimeout(timer);
    };
  }, [done, shown]);

  const finish = useCallback(() => {
    markGreetingDone();
    setDone(true);
  }, []);

  // Opening Cedar by any route (the launcher, a "Ask Cedar about this"
  // link) answers the greeting too. Adjusted during render, the way React
  // documents deriving state from a prop, rather than in an effect.
  if (cedarOpen && !done) {
    markGreetingDone();
    setDone(true);
  }

  if (done || !shown || cedarOpen) return null;

  return (
    <div className="cp-greet" role="status">
      <button
        type="button"
        className="cp-greet__open"
        onClick={() => {
          finish();
          onOpen();
        }}
      >
        Hi, I&rsquo;m Cedar. I&rsquo;m here to help with the collections, what they hold and how
        to use them.
      </button>
      <button type="button" className="cp-greet__dismiss" aria-label="Dismiss this message" onClick={finish}>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <line x1="6" y1="6" x2="18" y2="18" />
          <line x1="18" y1="6" x2="6" y2="18" />
        </svg>
      </button>
    </div>
  );
}
