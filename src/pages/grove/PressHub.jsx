// The hub: the whole reader behind four squares.
//
// One page held everything and curated it well on a wide screen, but on a
// phone the same page was a quarter hour of thumb. The hub gives every kind
// of thing its own page and puts four doors on the front — articles, data,
// what's new, methods — as literal squares, sized like the collection tiles
// because those squares already proved the size on both pointers. The same
// grid renders on desktop and phone (one row where it fits, 2x2 where it
// does not), so the two experiences stay symmetric instead of diverging.
//
// Every tile carries a ? in its corner: point at it (or tap it) and the
// line below the grid says what is behind the door. The ? is its own
// control beside the tile's link, never inside it, because a button inside
// an anchor is two answers to one tap.
import { useState } from "react";
import { Link } from "react-router";

import {
  PRESS_ARTICLES_PATH,
  PRESS_DATA_PATH,
  PRESS_METHODS_PATH,
  PRESS_WHATS_NEW_PATH,
} from "../../features/grove/pressRoutes";
import {
  CredibleResearchIcon,
  InsightsIcon,
  OriginalCollectionsIcon,
} from "./pressGateIcons";

// The gate icons' own contract, so the fourth glyph reads as family.
const glyph = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

/** A clock catching up to now: releases, dated. */
const WhatsNewIcon = (
  <svg {...glyph}>
    <path d="M4.5 7.5A9 9 0 1 1 3 12" />
    <path d="M3 3.5v4h4" />
    <path d="M12 7.6V12l3.4 2.2" />
  </svg>
);

const DOORS = [
  {
    id: "articles",
    label: "Articles",
    to: PRESS_ARTICLES_PATH,
    icon: InsightsIcon,
    what: "The Data Briefs: original research built from the collections, newest first.",
  },
  {
    id: "data",
    label: "Data",
    to: PRESS_DATA_PATH,
    icon: OriginalCollectionsIcon,
    what: "The collections themselves: what each one holds, and the release a click or tap away.",
  },
  {
    id: "whats-new",
    label: "What’s new",
    to: PRESS_WHATS_NEW_PATH,
    icon: WhatsNewIcon,
    what: "Every release, dated and versioned, so anything you downloaded or cited can be traced.",
  },
  {
    id: "methods",
    label: "Methods",
    to: PRESS_METHODS_PATH,
    icon: CredibleResearchIcon,
    what: "How the collections are built, sourced and kept current — the reference for citing a number.",
  },
];

const IDLE_NOTE =
  "The whole reader, four doors. The ? on a tile says what is behind it.";

export default function PressHub() {
  const [help, setHelp] = useState(null);
  const note = DOORS.find((door) => door.id === help)?.what;
  return (
    <section className="cp-sec cp-hub" aria-label="Inside Cedar Press">
      <span className="cp-sec__band">Inside Cedar Press</span>
      <ul className="cp-hub__grid">
        {DOORS.map((door) => (
          <li key={door.id}>
            <Link className="cp-hub__tile" to={door.to}>
              <span className="cp-hub__mark" aria-hidden="true">{door.icon}</span>
              <span className="cp-hub__name">{door.label}</span>
            </Link>
            <button
              type="button"
              className="cp-hub__help"
              aria-label={`What is behind ${door.label}?`}
              aria-expanded={help === door.id}
              onClick={() => setHelp(door.id)}
              onMouseEnter={() => setHelp(door.id)}
              onFocus={() => setHelp(door.id)}
            >
              ?
            </button>
          </li>
        ))}
      </ul>
      {/* aria-live, so a screen reader hears the answer the ? paints. */}
      <p className="cp-hub__note" aria-live="polite">{note || IDLE_NOTE}</p>
    </section>
  );
}
