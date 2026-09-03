// REVIEW OWNER: Havala
//
// One sponsorship slot.
//
// Renders the booked creative; or, on a slot that carries one, the invitation
// to buy the space; or the dashed outline under `?ads=demo`; or nothing at
// all. Nothing at all is still the answer for every slot not marked `house`,
// and it is still no element — no border, no reserved height, no margin
// collapsing into the gap where a unit would have been.
//
// The label sits above the unit rather than under it, in the page's mono
// chrome register, because a reader should know what they are looking at
// before they have looked at it. That holds for the invitation too: it says
// "Sponsorship" above itself, so nobody mistakes a house panel for editorial.

import {
  AD_ENQUIRY_HREF,
  AD_HOUSE,
  adsPreview,
  creativeFor,
  slotSpec,
} from "../../features/grove/pressAds";

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

  // Unsold, on a slot that carries the invitation. Not aria-hidden: unlike
  // the preview outline this says something, and the people it is addressed
  // to are readers of the page.
  if (spec.house) {
    return (
      <aside className={`cp-ad cp-ad--${spec.shape} cp-ad--house`} aria-label="Sponsorship">
        <span className="cp-ad__cap">{AD_HOUSE.cap}</span>
        <div className="cp-ad__house">
          <p className="cp-ad__housetitle">{AD_HOUSE.title}</p>
          <p className="cp-ad__housebody">{AD_HOUSE.body}</p>
          <a className="cp-ad__houseact" href={AD_ENQUIRY_HREF} target="_blank" rel="noreferrer">
            {AD_HOUSE.action} <span aria-hidden="true">&#8594;</span>
          </a>
        </div>
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
