/**
 * The scroll signal, as a hook.
 *
 * Its own file because a component module that also exports a hook breaks
 * fast refresh, and a page this long is one you want to iterate on without
 * losing scroll position every save.
 */
import { useEffect, useRef } from "react";

import { trackParallax } from "./pressAtmosphere";

/** Attaches the scroll signal and hands back the ref to hang it on. */
export function useParallax(strength = 1) {
  const ref = useRef(null);
  useEffect(() => trackParallax(ref.current, { strength }), [strength]);
  return ref;
}
