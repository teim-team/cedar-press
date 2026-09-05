/**
 * PURPOSE
 * Whether this device points with a finger. A phone has no hover, so every
 * "point at" affordance becomes "tap", and copy that says "point at" on a
 * touch screen describes something the reader cannot do. One answer, read
 * once, shared by every surface that words an affordance.
 */
export const COARSE =
  typeof window !== "undefined" && !!window.matchMedia?.("(hover: none), (pointer: coarse)").matches;
