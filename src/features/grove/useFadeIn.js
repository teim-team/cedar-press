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
import { useEffect, useLayoutEffect, useRef } from "react";

/** Nodes on the first screen are revealed with the page, not after it. */
const FIRST_SCREEN_SLACK = 1.1;

export function useFadeIn() {
  const root = useRef(null);

  // useLayoutEffect, not useEffect: this has to run BEFORE the browser
  // paints. In an effect the sections would paint at opacity 0 and then be
  // corrected, which is the flash this is here to remove. The measurement it
  // makes is a getBoundingClientRect against the fold, which is cheap and
  // needs no observer.
  useLayoutEffect(() => {
    const nodes = root.current?.querySelectorAll(".cp-fade");
    if (!nodes) return;
    // Slack, because this runs before webfonts have resolved and the fold is
    // a few lines further down once they do. Over-revealing by one section is
    // invisible; under-revealing brings the stagger back.
    const fold = (window.innerHeight || 0) * FIRST_SCREEN_SLACK;
    for (const node of nodes) {
      if (node.getBoundingClientRect().top < fold) node.classList.add("is-in", "cp-fade--now");
    }
  }, []);

  useEffect(() => {
    // Only what the layout effect left alone: the sections below the fold.
    const nodes = [...(root.current?.querySelectorAll(".cp-fade:not(.is-in)") ?? [])];
    if (!nodes.length) return undefined;
    if (typeof IntersectionObserver === "undefined") {
      nodes.forEach((node) => node.classList.add("is-in"));
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            observer.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "-6% 0px" },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  return root;
}
