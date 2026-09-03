// REVIEW OWNER: Havala
//
// The layers behind the page.
//
// Contour lines and a halo, drifting at a fraction of scroll speed. They live
// behind everything and never carry meaning, so a reader who never notices
// them has lost nothing and a reader who does gets some depth behind a page
// whose surfaces are otherwise flat blocks of colour.
//
// There was a third layer, an oversized ghost word behind each section. It is
// deleted rather than disabled: the founder read it as noise, and a decorative
// layer nobody wants is not worth the flag to turn it off.
//
// Everything here is aria-hidden and pointer-events: none. It is atmosphere.

import { useParallax } from "../../features/grove/useParallax";

/**
 * Topographic contours. Drawn rather than an image so they inherit the
 * section's own colour and cost nothing to load, and kept to a handful of
 * long curves: a dense contour map reads as decoration for its own sake.
 */
export function Contours({ className = "", strength = 1 }) {
  const ref = useParallax(strength);
  return (
    <svg
      ref={ref}
      className={`cp-atmo cp-atmo--contour ${className}`}
      viewBox="0 0 1200 600"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
    >
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <path
          key={i}
          d={`M-40 ${120 + i * 74} C 220 ${60 + i * 74}, 420 ${210 + i * 74}, 640 ${150 + i * 74} S 1020 ${40 + i * 74}, 1240 ${130 + i * 74}`}
        />
      ))}
    </svg>
  );
}

/** A faint ring, for a corner that would otherwise be flat colour. */
export function Halo({ className = "", strength = 1 }) {
  const ref = useParallax(strength);
  return (
    <span ref={ref} className={`cp-atmo cp-atmo--halo ${className}`} aria-hidden="true" />
  );
}
