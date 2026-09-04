// Reveal-on-scroll for long public pages: elements marked `cp-fade` under
// the returned ref arrive as they enter the viewport, once — a section that
// has been seen stays seen, like the shelf bands. Anywhere without
// IntersectionObserver reveals everything immediately, and
// prefers-reduced-motion stills the whole thing in CSS.
//
// WHAT IS ALREADY ON SCREEN IS NOT A REVEAL
// A scroll reveal is for something the reader scrolls to. Applied to the
// first screen it is something else: the page has already run its own
// `cp-page-in` rise, and then every section on that screen rises again, a
// beat later and on its own timer, because an IntersectionObserver callback
// cannot fire until after the first paint. Sampling the viewport every ~50ms
// through a load measured that as a train of distinct frames running from
// 1179ms to 1427ms on the reader — the page arriving, and then arriving
// again in pieces. That is the "sections popping in at different moments"
// this hook is now written to avoid.
//
// So the split is by position: anything intersecting the first screen is
// revealed at attach time and told not to transition, so it is simply part of
// the page when the page appears. Everything below the fold keeps the
// observer and the 0.55s rise it was written for.
//
// ============================================================================
// THE READER WENT BLANK AFTER SIGN-IN. TWO CAUSES, BOTH HERE.
// ============================================================================
// Reported 2026-09-03 on mobile and desktop, and again on 2026-09-04 after
// the first fix: sign in, and the page shows the masthead and the ad and
// nothing else. `.cp-fade` is `opacity: 0` in CSS and is revealed only by
// JavaScript adding `is-in`, so a revealer that never runs is not a slow page.
// It is a permanently invisible one.
//
// CAUSE 1 — the subtree was empty at mount.
// `CedarPress.jsx` renders its whole body behind `{loading ? null : ...}`.
// Connected, `loading` starts true, so at mount there were no `.cp-fade`
// nodes: the effect matched nothing and returned early on `if (!nodes.length)`,
// so no IntersectionObserver was ever constructed. `/me` answered, the
// sections mounted at opacity 0, and nothing was left alive to reveal them.
// Fixed by watching for nodes that arrive later — see `attachFadeIn`.
//
// CAUSE 2 — the ref detaches and reattaches, and a mount-time effect does not.
// This is the one that survived the first fix, and it is why signing out and
// back in still reproduced it. `CedarPress.jsx` has an EARLY RETURN:
//
//     if (!loading && !entitled) return (<div><PressGate /></div>);   // no ref
//     ...
//     return (<main ref={fadeRoot}> ... </main>);                     // ref
//
// So for a reader who arrives signed out:
//   1. mount, `loading` true    -> main branch, ref attaches, observer starts
//   2. session says not entitled -> gate branch, React sets the ref to NULL
//                                   and the effect cleanup disconnects
//   3. they sign in              -> main branch again, ref points at a NEW
//                                   element - and `useEffect(..., [])` never
//                                   runs again. No observer. Blank page.
//
// A `useRef` plus a mount-time effect cannot see step 3 at all: the ref object
// is stable, so nothing tells React to re-run anything when the element behind
// it changes. That is what a CALLBACK REF is for. React invokes it with the
// node on attach and with null on detach, every time, so the observers follow
// the element instead of following the component's first render.
//
// It also runs during the commit phase, before paint, which is the property
// the old `useLayoutEffect` was chosen for — so the first-screen sections
// still appear with the page rather than a frame later.
//
// Readers with `prefers-reduced-motion` were never affected: the CSS reveals
// everything for them, which is part of why this survived review twice.
import { useCallback, useRef } from "react";

/** Nodes on the first screen are revealed with the page, not after it. */
const FIRST_SCREEN_SLACK = 1.1;

/** On the first screen: revealed immediately, and told not to transition. */
function revealNow(node) {
  node.classList.add("is-in", "cp-fade--now");
}

/**
 * Split freshly-seen nodes by position. Returns those left for the observer.
 *
 * Nodes arriving after first paint are already on a painted page, so one above
 * the fold then is something the reader is looking at right now and must
 * appear without a stagger — the same rule, for the same reason.
 *
 * Slack, because this can run before webfonts have resolved and the fold is a
 * few lines further down once they do. Over-revealing by one section is
 * invisible; under-revealing brings the stagger back.
 */
function splitByFold(nodes) {
  const fold = (window.innerHeight || 0) * FIRST_SCREEN_SLACK;
  const below = [];
  for (const node of nodes) {
    if (node.classList.contains("is-in")) continue;
    if (node.getBoundingClientRect().top < fold) revealNow(node);
    else below.push(node);
  }
  return below;
}

/**
 * Everything the reveal does, as a plain function over an element.
 *
 * Extracted so it can be TESTED. This project's harness is `node --test` with
 * no jsdom, so logic inside a hook was unreachable from a test — which is a
 * large part of why a page that renders nothing shipped twice.
 *
 * Returns a cleanup, and takes ownership of the element until it is called.
 */
export function attachFadeIn(el) {
  if (!el) return () => {};

  // No IntersectionObserver: reveal everything, now and whenever more arrives.
  // Never leave content at opacity 0 because a capability is absent.
  const canObserve = typeof IntersectionObserver !== "undefined";

  const observer = canObserve
    ? new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-in");
              observer.unobserve(entry.target);
            }
          }
        },
        { rootMargin: "-6% 0px" },
      )
    : null;

  const take = (nodes) => {
    const list = [...nodes].filter((n) => !n.classList.contains("is-in"));
    if (!list.length) return;
    if (!observer) {
      list.forEach((n) => n.classList.add("is-in"));
      return;
    }
    splitByFold(list).forEach((n) => observer.observe(n));
  };

  take(el.querySelectorAll(".cp-fade"));

  // Content that mounts after the session resolves — cause 1 above.
  if (typeof MutationObserver === "undefined") {
    el.querySelectorAll(".cp-fade").forEach((n) => n.classList.add("is-in"));
    return () => observer?.disconnect();
  }

  const mutations = new MutationObserver((records) => {
    const found = [];
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (node.classList?.contains("cp-fade")) found.push(node);
        const inner = node.querySelectorAll?.(".cp-fade");
        if (inner?.length) found.push(...inner);
      }
    }
    if (found.length) take(found);
  });
  mutations.observe(el, { childList: true, subtree: true });

  return () => {
    mutations.disconnect();
    observer?.disconnect();
  };
}

/**
 * A CALLBACK ref. Attach it with `ref={fadeRoot}` exactly as before.
 *
 * Callback and not `useRef`, for cause 2 above: React calls this with the node
 * every time the element behind the ref changes, including null on detach, so
 * a component that returns a different tree on a later render still gets its
 * observers. A mount-time effect cannot see that happen.
 */
export function useFadeIn() {
  const cleanup = useRef(null);
  return useCallback((node) => {
    if (cleanup.current) {
      cleanup.current();
      cleanup.current = null;
    }
    if (node) cleanup.current = attachFadeIn(node);
  }, []);
}
