// Reveal-on-scroll for long public pages: elements marked `cp-fade` under
// the returned ref arrive as they enter the viewport, once — a section that
// has been seen stays seen, like the shelf bands. Anywhere without
// IntersectionObserver reveals everything immediately, and
// prefers-reduced-motion stills the whole thing in CSS.
import { useEffect, useRef } from "react";

export function useFadeIn() {
  const root = useRef(null);
  useEffect(() => {
    const nodes = [...(root.current?.querySelectorAll(".cp-fade") ?? [])];
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
