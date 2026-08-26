// The hub: the whole reader behind four squares.
//
// One page held everything and curated it well on a wide screen, but on a
// phone the same page was a quarter hour of thumb. The hub gives every kind
// of thing its own page and puts four doors on the front — articles, data,
// what's new, methods, want more, feedback — as literal squares, sized like the collection tiles
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
  ArticlesIcon,
  DataIcon,
  FeedbackIcon,
  MethodsIcon,
  WantMoreIcon,
  WhatsNewIcon,
} from "./pressHubIcons";

const DOORS = [
  {
    id: "articles",
    label: "Articles",
    to: PRESS_ARTICLES_PATH,
    icon: ArticlesIcon,
    what: "The Data Briefs: original research built from the collections, newest first.",
  },
  {
    id: "data",
    label: "Data",
    to: PRESS_DATA_PATH,
    icon: DataIcon,
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
    icon: MethodsIcon,
    what: "How the collections are built, sourced and kept current — the reference for citing a number.",
  },
  // The upgrade path earns a door: the shelves a plan does not include yet
  // live on the data page, under the locked band and the Grove boundary.
  {
    id: "more",
    label: "Want more",
    to: `${PRESS_DATA_PATH}#grove`,
    icon: WantMoreIcon,
    what: "What your plan does not include yet — Cedar Press+ and Cedar Grove — and the way to get each.",
  },
  // Feedback is surfaced, not buried in the footer: it goes to the team
  // that builds the datasets and shapes what gets built next.
  {
    id: "feedback",
    label: "Send feedback",
    href: "mailto:contact@lumecon.ai?subject=Cedar%20Press%20feedback",
    icon: FeedbackIcon,
    what: "Tell the team what the data should do next, or what a page gets wrong. A person reads it.",
  },
];

const IDLE_NOTE =
  "The whole reader, six doors. The ? on a tile says what is behind it.";

export default function PressHub() {
  const [help, setHelp] = useState(null);
  const note = DOORS.find((door) => door.id === help)?.what;
  return (
    <section className="cp-sec cp-hub" aria-label="Inside Cedar Press">
      <span className="cp-sec__band">Inside Cedar Press</span>
      <ul className="cp-hub__grid">
        {DOORS.map((door) => (
          <li key={door.id}>
            {door.href ? (
              <a className="cp-hub__tile" href={door.href}>
                <span className="cp-hub__mark" aria-hidden="true">{door.icon}</span>
                <span className="cp-hub__name">{door.label}</span>
              </a>
            ) : (
              <Link className="cp-hub__tile" to={door.to}>
                <span className="cp-hub__mark" aria-hidden="true">{door.icon}</span>
                <span className="cp-hub__name">{door.label}</span>
              </Link>
            )}
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
