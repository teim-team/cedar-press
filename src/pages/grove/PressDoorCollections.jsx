// REVIEW OWNER: Havala
//
// The twelve, on the door, at a size a visitor can point at.
//
// The owner's ask, 2026-09-13: "on the pre-login page, is there a spot where
// the twelve dataset strip could be, so you can preview what you're getting."
//
// The frame above this already lists all twelve down its rail, and that rail
// has always been clickable. But the frame renders the real app at 1280px and
// scales it to fit, which lands around 0.63: each rail row is roughly
// seventeen pixels tall, the labels are six-point type, and nothing on the
// page said any of it was live. A visitor deciding whether to subscribe could
// see that twelve things exist and not what any of them holds.
//
// So: the same twelve, full size, below the frame they drive. Pointing at one
// swaps the frame above AND answers in the line below, so it works whether or
// not the frame is still on screen at that scroll position.
//
// BOTH SHELVES, LABELLED. The question a visitor actually has is what comes
// with which plan, so the strip groups by tier and says so. Hiding the six
// behind the upgrade would answer the wrong question.
//
// Nothing here is written: the names, the blurbs, the row counts and the
// coverage all come from the catalog and the launch descriptors, so the strip
// cannot advertise a collection the storefront does not sell.

import { COARSE } from "../../features/grove/pointer.js";
import { coverageLabel } from "../../features/grove/pressAccess";
import { PRESS_TIERS, STOREFRONT_CATALOG } from "../../features/grove/pressCatalog";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { TierName } from "./TierName";

const ROWS_LABEL = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry.rowsLabel]));

/** The storefront tiers, each with the collections on its shelf. */
const SHELVES = PRESS_TIERS.filter((tier) => tier.storefront).map((tier) => ({
  tier,
  entries: STOREFRONT_CATALOG.filter((entry) => entry.shelf === tier.shelf),
}));

// On a phone the frame is a long way up the page by the time this is on
// screen, so the coarse copy does not promise a window the reader cannot see.
const IDLE = COARSE
  ? "Tap a collection for what it holds."
  : "Point at a collection to see it in the window above.";

export default function PressDoorCollections({ selectedId, onPick, onPoint }) {
  const active = STOREFRONT_CATALOG.find((entry) => entry.id === selectedId) ?? null;
  const tierOf = (entry) => SHELVES.find((shelf) => shelf.tier.shelf === entry.shelf)?.tier ?? null;

  return (
    <section className="cp-dcol cp-fade" aria-label="The twelve collections">
      <div className="cp-dcol__head">
        <span className="cp-kicker">What you get</span>
        <p className="cp-dcol__lede">
          Twelve collections, {STOREFRONT_CATALOG.length === 12 ? "six on each plan" : "across two plans"}.
        </p>
      </div>

      {SHELVES.map(({ tier, entries }) => (
        /* The shelf whose collection is in hand carries `is-active`, so the
           strip also answers which plan the pointed collection comes with;
           the CSS makes that a colour, never a movement. */
        <div className={`cp-dcol__shelf${active?.shelf === tier.shelf ? " is-active" : ""}`} key={tier.id}>
          <span className="cp-dcol__tier">
            <TierName name={tier.name} />
            <small>{tier.question}</small>
          </span>
          <ul className="cp-dcol__grid">
            {entries.map((entry, i) => {
              const on = entry.id === selectedId;
              return (
                /* `--i` is the tile's place on its shelf: the stylesheet
                   staggers the shelf's arrival on it, left to right. */
                <li key={entry.id} style={{ "--i": i }}>
                  <button
                    type="button"
                    className={`cp-dcol__tile${on ? " is-on" : ""}`}
                    aria-pressed={on}
                    onClick={() => onPick(entry)}
                    onMouseEnter={() => onPoint(entry.id)}
                    onFocus={() => onPoint(entry.id)}
                  >
                    <span className="cp-dcol__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
                    <span className="cp-dcol__name">
                      <TierName name={entry.short || entry.name} />
                    </span>
                    {ROWS_LABEL[entry.id] ? <span className="cp-dcol__rows">{ROWS_LABEL[entry.id]}</span> : null}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}

      {/* aria-live, so a reader who cannot see the window above still hears
          what the pointer selected. */}
      <p className="cp-dcol__note" aria-live="polite">
        {active ? (
          <>
            <b>{active.name}.</b> {active.blurb}{" "}
            <span className="cp-dcol__meta">
              {coverageLabel(active)}
              {tierOf(active) ? <> &middot; <TierName name={tierOf(active).name} /></> : null}
            </span>
          </>
        ) : (
          IDLE
        )}
      </p>
    </section>
  );
}
