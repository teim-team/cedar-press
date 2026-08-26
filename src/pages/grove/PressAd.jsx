// REVIEW OWNER: Havala
//
// One sponsorship slot.
//
// Renders the booked creative, or the dashed outline under `?ads=demo`, or
// nothing at all. Nothing at all is the default and the state to check first:
// no element, so no border, no reserved height and no margin collapsing into
// the gap where a unit would have been.
//
// The label sits above the unit rather than under it, in the page's mono
// chrome register, because a reader should know what they are looking at
// before they have looked at it.

import { adsPreview, creativeFor, slotSpec } from "../../features/grove/pressAds";

const preview = () =>
  adsPreview(typeof window === "undefined" ? "" : window.location.search);

export default function PressAd({ slot }) {
  const spec = slotSpec(slot);
  if (!spec) return null;

  const creative = creativeFor(slot);
  if (creative) {
    return (
      <aside className={`cp-ad cp-ad--${spec.shape}`} aria-label="Sponsored">
        <span className="cp-ad__cap">Sponsored</span>
        <a className="cp-ad__unit" href={creative.href} target="_blank" rel="noreferrer sponsored">
          <img src={creative.image} alt={creative.alt} loading="lazy" />
        </a>
      </aside>
    );
  }

  if (!preview()) return null;

  // Preview only. aria-hidden because it describes a layout rather than
  // saying anything, and a screen reader announcing "article rail 300 by
  // 250" in the middle of a piece is noise.
  return (
    <aside
      className={`cp-ad cp-ad--${spec.shape} cp-ad--empty`}
      aria-hidden="true"
      style={spec.shape === "box" ? { aspectRatio: spec.ratio } : { minHeight: spec.height }}
    >
      <span className="cp-ad__cap">Sponsored</span>
      <span className="cp-ad__slot">
        <b>{spec.name}</b>
        {spec.size}
      </span>
    </aside>
  );
}
