// REVIEW OWNER: Havala
//
// The twelve collections, as a strip you can point at.
//
// The owner's ask, 2026-09-13: "if there was an elegant way to have quick
// buttons of the datasets you can hover over and see them, that would be cool
// if it fits anywhere, if there's a blank spot for it."
//
// The blank spot was the overview, between the six section tiles and the
// priorities block. The Collections tile there says "12 COLLECTIONS" and then
// makes the reader open a page to find out which twelve. This is those twelve,
// each a direct link into Explore already narrowed to it.
//
// SAME POINT-TO-READ LANGUAGE AS EVERYTHING ELSE. The shelves do it, the
// section tiles above do it, and the Methods index does it: point at a mark,
// read the answer in a line under the grid, and the selection is sticky so it
// can be read at leisure. A twelfth variant of the same idea would be a
// thirteenth thing for a reader to learn.
//
// Nothing here is written. The names, the blurbs and the coverage come from
// the catalog, and the marks from the same set the shelf and Methods use, so
// the strip cannot name a collection the storefront does not sell.

import { useState } from "react";
import { Link } from "react-router";

import { COARSE } from "../../features/grove/pointer.js";
import { canOpenDataset, coverageLabel } from "../../features/grove/pressAccess";
import { STOREFRONT_CATALOG } from "../../features/grove/pressCatalog";
import { PRESS_DATA_PATH } from "../../features/grove/pressRoutes";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { COLLECTION_ICONS } from "./pressCollectionIcons";

// Codex, PR #79: on a coarse pointer there is no hover and the tile is a
// link, so a tap navigated to the collection immediately and the reader never
// saw the line this promised. Two honest options: make the first tap select
// and the second open, or say what the tap actually does. A strip of twelve
// links whose first tap does nothing visible is a worse trade on a phone than
// a strip that opens what you touch, so the copy tells the truth and the
// description stays a pointer affordance.
const IDLE = COARSE
  ? "Tap a collection to open it."
  : "Point at a collection for what it holds.";

export default function PressCollectionStrip({ user }) {
  const [help, setHelp] = useState(null);
  const shown = STOREFRONT_CATALOG;
  const active = shown.find((entry) => entry.id === help) ?? null;

  return (
    <section className="cp-sec cp-cstrip cp-fade" aria-label="The collections">
      <span className="cp-sec__band">The collections</span>
      <ul className="cp-cstrip__grid">
        {shown.map((entry) => {
          // A collection this plan does not open still shows: knowing what
          // exists is the point of a strip, and the tile says which it is
          // rather than pretending the shelf is shorter than it is.
          const open = canOpenDataset(user, entry);
          const watch = {
            onMouseEnter: () => setHelp(entry.id),
            onFocus: () => setHelp(entry.id),
            onClick: () => track(EVENT.sectionOpened, { section: `strip:${entry.id}` }),
          };
          return (
            <li key={entry.id}>
              <Link
                className={`cp-cstrip__tile${open ? "" : " is-locked"}${help === entry.id ? " is-on" : ""}`}
                to={`${PRESS_DATA_PATH}?c=${entry.id}`}
                {...watch}
              >
                <span className="cp-cstrip__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
                <span className="cp-cstrip__name">{entry.short ?? entry.name}</span>
                {open ? null : <span className="cp-badge__sr">(not on your plan)</span>}
              </Link>
            </li>
          );
        })}
      </ul>
      {/* aria-live, so a screen reader hears the answer the pointer paints. */}
      <p className="cp-cstrip__note" aria-live="polite">
        {active ? (
          <>
            <b>{active.name}.</b> {active.blurb}{" "}
            <span className="cp-cstrip__meta">
              {coverageLabel(active)}
              {canOpenDataset(user, active) ? "" : " · not on your plan"}
            </span>
          </>
        ) : (
          IDLE
        )}
      </p>
    </section>
  );
}
