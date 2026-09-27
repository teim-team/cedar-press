// REVIEW OWNER: Havala
//
// The house duotones (owner, 2026-09-27): "we have like four or five
// different colors, green, yellow, whatever. Make it more interesting."
//
// These are lumecon.ai's washes, shadow -> highlight, copied from
// lumecon-website/scripts/naics/sectors.mjs, where they tone the sector
// photography: teal, bronze, gold, green and slate. The "gold" wash is the
// amber data-accent family, not the brand-only wordmark gold.
//
// The page applies them through the SVG filters in index.html
// (`#cp-duo-<name>`, one per wash); the article PDF applies the same ramp to
// the pixels itself, so a picture reads the same on screen and on paper.

export const DUOTONES = Object.freeze({
  teal: Object.freeze({ shadow: [9, 68, 74], highlight: [134, 191, 186] }),
  bronze: Object.freeze({ shadow: [49, 32, 34], highlight: [170, 151, 142] }),
  gold: Object.freeze({ shadow: [117, 87, 34], highlight: [241, 210, 147] }),
  green: Object.freeze({ shadow: [31, 60, 54], highlight: [133, 160, 146] }),
  slate: Object.freeze({ shadow: [23, 38, 48], highlight: [150, 163, 170] }),
});

export const DEFAULT_TONE = "teal";

/** A known wash name, falling back to teal for anything else. */
export function toneOf(name) {
  return Object.hasOwn(DUOTONES, name ?? "") ? name : DEFAULT_TONE;
}

/** The class a toned picture carries; press.css maps it to its filter. */
export const toneClass = (name) => `cp-tone--${toneOf(name)}`;

/**
 * Map RGBA pixels through a wash in place: luminance (Rec. 709) from shadow
 * to highlight, alpha untouched. Pure, so it is testable without a canvas.
 */
export function applyDuotone(data, name) {
  const { shadow, highlight } = DUOTONES[toneOf(name)];
  for (let i = 0; i < data.length; i += 4) {
    const g = (0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2]) / 255;
    data[i] = Math.round(shadow[0] + (highlight[0] - shadow[0]) * g);
    data[i + 1] = Math.round(shadow[1] + (highlight[1] - shadow[1]) * g);
    data[i + 2] = Math.round(shadow[2] + (highlight[2] - shadow[2]) * g);
  }
  return data;
}
