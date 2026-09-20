// The rail of collections. One component, three surfaces.
//
// WHY THIS EXISTS
// Cedar Press had three separately authored ways of showing the same twelve
// collections: the door's scaled product frame drew its own navy rail, the
// signed-in page drew tier bands of square badges, and the viewer under them
// drew a dropdown. Three grammars for one list, which is how a reader comes
// to think the landing page's table and the product's table are different
// products.
//
// So the rail is one component and the surfaces differ by MODE, not by
// markup. Per the implementation brief's Priority 0: the rail, the selected
// collection and the table geometry are structurally shared, and what
// changes between surfaces is what the reader may do, never what they are
// looking at.
//
// WHAT A MODE CHANGES
//   "preview"  the door. Every collection is pointable, nothing is locked,
//              because nobody is signed in and the question is what exists.
//   "app"      behind the paywall. A collection this subscription cannot
//              open stays in the rail, selectable, visibly locked. That is
//              the brief's Priority 1: a Cedar Press reader should be able
//              to see and understand a Plus collection, and be told in place
//              what opens it, rather than have it hidden or be thrown out to
//              a plans page.
//
// The lock here is an affordance and nothing else. `pressAccess` says so in
// its own header and it is worth repeating: the server has to refuse the
// same request, and a client that dims a row has not protected anything.
import { canOpenDataset } from "../../features/grove/pressAccess";
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

/**
 * @param selectedId  the collection the surface beside this is showing
 * @param onSelect    (entry) => void
 * @param onPoint     optional; the door answers a line under the rail on hover
 * @param user        null in preview mode; decides what is locked in app mode
 * @param mode        "preview" | "app"
 * @param allLabel    optional first row, e.g. "All 12 collections"
 */
export default function PressCollectionRail({
  selectedId,
  onSelect,
  onPoint = null,
  user = null,
  mode = "app",
  allLabel = null,
}) {
  return (
    <nav className={`cp-rail cp-rail--${mode}`} aria-label="Collections">
      {allLabel ? (
        <button
          type="button"
          className={`cp-rail__item cp-rail__item--all${selectedId ? "" : " is-on"}`}
          aria-pressed={!selectedId}
          onClick={() => onSelect(null)}
        >
          <span className="cp-rail__name">{allLabel}</span>
        </button>
      ) : null}
      {SHELVES.map(({ tier, entries }) => (
        <div className="cp-rail__shelf" key={tier.id}>
          <span className="cp-rail__tier">
            <TierName name={tier.name} />
          </span>
          <ul className="cp-rail__list">
            {entries.map((entry) => {
              const on = entry.id === selectedId;
              // In preview nothing is locked: there is no subscription to
              // measure against, and greying half the catalogue on the door
              // answers a question nobody asked yet.
              const locked = mode === "app" && !canOpenDataset(user, entry);
              return (
                <li key={entry.id}>
                  <button
                    type="button"
                    className={`cp-rail__item${on ? " is-on" : ""}${locked ? " is-locked" : ""}`}
                    aria-pressed={on}
                    onClick={() => onSelect(entry)}
                    onMouseEnter={onPoint ? () => onPoint(entry.id) : undefined}
                    onFocus={onPoint ? () => onPoint(entry.id) : undefined}
                  >
                    <span className="cp-rail__mark" aria-hidden="true">
                      {COLLECTION_ICONS[entry.id] ?? null}
                    </span>
                    <span className="cp-rail__text">
                      <span className="cp-rail__name">
                        <TierName name={entry.short || entry.name} />
                      </span>
                      {ROWS_LABEL[entry.id] ? (
                        <span className="cp-rail__rows">{ROWS_LABEL[entry.id]}</span>
                      ) : null}
                    </span>
                    {/* Named, not a padlock glyph. A reader who cannot open
                        something is owed the name of the thing that opens
                        it, and "Plus" is shorter than the icon's tooltip. */}
                    {locked ? <span className="cp-rail__lock">Plus</span> : null}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
