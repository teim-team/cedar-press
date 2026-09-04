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
// So the split is by position, decided once, before the browser paints:
// anything intersecting the first screen is marked revealed in a layout
// effect and told not to transition, so it is simply part of the page when
// the page appears. Everything below the fold keeps the observer and the
// 0.55s rise it was written for.
//
// THE BUG THIS COST, AND WHY THE MUTATION OBSERVER IS NOT OPTIONAL
// -----------------------------------------------------------------
// Reported 2026-09-03, on mobile AND desktop: after signing in, the page
// showed one band and nothing else until a manual refresh.
//
// Both effects below used to run ONCE, on mount, with `[]` deps. On the
// reader, `CedarPress.jsx` gates its whole body on the session:
//
//     {loading ? null : ( ...every cp-fade section... )}
//
// Connected, `loading` starts TRUE, so at mount there are no `.cp-fade`
// nodes at all. The layout effect matched nothing. The scroll effect matched
// nothing and returned early on `if (!nodes.length)`, so **no observer was
// ever created**. Then `/me` answered, `loading` flipped, and the sections
// mounted carrying `cp-fade` — which is `opacity: 0` in CSS — with nothing
// left alive to ever add `is-in`. The page was not slow. It was permanently
// invisible, and only a reload (where the session resolves before first
// paint) recovered it.
//
// That is the worst failure shape available to this pattern: content hidden
// by default, revealed by JavaScript, where the revealer can miss. So the
// hook no longer assumes the subtree is complete at mount. It watches for
// `cp-fade` nodes that arrive later and gives them the same first-screen /
// below-fold treatment. Adding `loading` to a dependency array would have
// fixed this one page; every future page that renders its body behind an
// await would have re-introduced it.
//
// Readers with `prefers-reduced-motion` were never affected — the CSS
// reveals everything for them — which is part of why this survived review.
import { useEffect, useLayoutEffect, useRef } from "react";

/** Nodes on the first screen are revealed with the page, not after it. */
const FIRST_SCREEN_SLACK = 1.1;

/** On the first screen: revealed immediately, and told not to transition. */
function revealNow(node) {
  node.classList.add("is-in", "cp-fade--now");
}

/**
 * Split freshly-seen nodes by position. Returns those left for the observer.
 *
 * `firstPaint` is true only for the layout effect that runs before the
 * browser paints. Nodes arriving LATER are already on a painted page, so a
 * node above the fold then is something the reader is looking at right now
 * and must appear without a stagger — same rule, same reason.
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
 * Everything the scroll effect does, as a plain function over an element.
 *
 * Extracted so it can be TESTED. This project's test harness is `node --test`
 * with no jsdom, so a hook body inside `useEffect` is unreachable from a test
 * — which is precisely why a bug that made the reader blank shipped. Given an
 * element and the two observer globals, this is drivable with stubs.
 *
 * Returns a cleanup, like the effect it serves.
 */
export function attachFadeIn(el) {
  if (!el) return () => {};

  // No IntersectionObserver: reveal everything, now and whenever more
  // arrives. Never leave a node at opacity 0 because a capability is absent.
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

  // Content that mounts after the session resolves — the case that made the
  // reader blank. `MutationObserver` is available everywhere this app runs;
  // if it somehow is not, reveal what is present rather than hide it.
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

export function useFadeIn() {
  const root = useRef(null);

  // useLayoutEffect, not useEffect: this has to run BEFORE the browser
  // paints. In an effect the sections would paint at opacity 0 and then be
  // corrected, which is the flash this is here to remove. The measurement it
  // makes is a getBoundingClientRect against the fold, which is cheap and
  // needs no observer.
  //
  // Slack, because this runs before webfonts have resolved and the fold is a
  // few lines further down once they do. Over-revealing by one section is
  // invisible; under-revealing brings the stagger back.
  useLayoutEffect(() => {
    const nodes = root.current?.querySelectorAll(".cp-fade");
    if (nodes) splitByFold([...nodes]);
  }, []);

  useEffect(() => attachFadeIn(root.current), []);

  return root;
}
