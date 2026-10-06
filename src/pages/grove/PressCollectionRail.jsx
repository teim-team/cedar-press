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
import { useState } from "react";

import { canOpenDataset } from "../../features/grove/pressAccess";
import { downloadAll } from "../../features/grove/pressDownload";
import { PRESS_TIERS, STOREFRONT_CATALOG } from "../../features/grove/pressCatalog";
import { LAUNCH_COLLECTION, sampleUnavailableReason } from "../../features/grove/collection";
import { recordStructure } from "../../features/grove/pressRecordStructure.js";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { TierName } from "./TierName";
import { coverageLabel } from "../../features/grove/pressAccess";
import { freshnessLine } from "../../features/grove/pressReleases";

const ROWS_LABEL = Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry.rowsLabel]));

/** The storefront tiers, each with the collections on its shelf. */
const SHELVES = PRESS_TIERS.filter((tier) => tier.storefront).map((tier) => ({
  tier,
  entries: STOREFRONT_CATALOG.filter((entry) => entry.shelf === tier.shelf),
}));

/** "Download all N samples", per shelf, from inside the rail. */
function ShelfDownload({ tier, entries }) {
  const [state, setState] = useState("idle");
  return (
    <button
      type="button"
      className="cp-rail__all"
      disabled={state === "busy"}
      onClick={async () => {
        setState("busy");
        try {
          await downloadAll(entries, `cedar-press-${tier.id}-examples.zip`);
          setState("idle");
        } catch {
          // Said, not swallowed: a download that quietly does nothing is
          // indistinguishable from a click that missed.
          setState("failed");
        }
      }}
    >
      {state === "busy" ? "Preparing" : state === "failed" ? "Try again" : `Download all ${entries.length}`}
      <span aria-hidden="true"> &#8595;</span>
    </button>
  );
}

/**
 * @param selectedId  the collection the surface beside this is showing
 * @param onSelect    (entry) => void
 * @param onPoint     optional; the door answers a line under the rail on hover
 * @param user        null in preview mode; decides what is locked in app mode
 * @param mode        "preview" | "app"
 * @param allLabel    optional first row, e.g. "All 12 collections"
 */
/**
 * The hover card (owner, 2026-10-06: "when you hover over a data set, it
 * tells you more"). In the app only: on the door, pointing at a collection
 * already opens it in the pane beside the rail, and the door's rail sits in a
 * scaled frame a floating card would be clipped by. Fixed-positioned beside
 * the item, so the rail's own scrolling cannot clip it; a mouse or keyboard
 * focus opens it, a tap never does.
 */
function RailTip({ tip }) {
  if (!tip) return null;
  const { entry, top, left } = tip;
  const facts = [coverageLabel(entry), ROWS_LABEL[entry.id], freshnessLine(entry.id)].filter(Boolean);
  return (
    <div className="cp-railtip" role="tooltip" id={`cp-railtip-${entry.id}`} style={{ top, left }}>
      <b className="cp-railtip__name"><TierName name={entry.name} /></b>
      {entry.blurb ? <p className="cp-railtip__blurb">{entry.blurb}</p> : null}
      {facts.length ? <p className="cp-railtip__facts">{facts.join(" \u00b7 ")}</p> : null}
    </div>
  );
}

const canHover = () =>
  typeof window !== "undefined" && window.matchMedia?.("(hover: hover) and (pointer: fine)").matches;

export default function PressCollectionRail({
  selectedId,
  onSelect,
  onPoint = null,
  user = null,
  mode = "app",
  allLabel = null,
}) {
  const [tip, setTip] = useState(null);
  const showTip = (entry, element) => {
    if (mode !== "app") return;
    const box = element.getBoundingClientRect();
    setTip({ entry, top: Math.max(8, box.top), left: box.right + 10 });
  };
  const hideTip = () => setTip(null);
  return (
    <nav className={`cp-rail cp-rail--${mode}`} aria-label="Collections" onScroll={hideTip}>
      <RailTip tip={tip} />
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
      {SHELVES.map(({ tier, entries }) => {
        // Samples only: a collection presented by its record structure opens
        // like any other but has no sample rows to put in the shelf's file.
        const sampleReady = entries.filter((entry) => canOpenDataset(user, entry) && !sampleUnavailableReason(entry.id) && !recordStructure(entry.id));
        const upgradeable = entries.filter((entry) => !canOpenDataset(user, entry) && !sampleUnavailableReason(entry.id));
        return (
          <div className="cp-rail__shelf" key={tier.id}>
          <span className="cp-rail__tier">
            <TierName name={tier.name} />
            {/* The one thing the tier bands did that nothing else does. They
                were deleted when the table became the Collections page, and
                a shelf's samples are a real feature, so the action came with
                the shelf rather than going with the band. Preview only on
                the door, where there is no subscription to download
                against. */}
            {mode === "app" && sampleReady.length ? (
              <ShelfDownload tier={tier} entries={sampleReady} />
            ) : null}
            {/* THE UPSELL BELONGS TO THE SHELF IT IS ABOUT.
                It was a line inside the table pane — "6 more collections on
                Cedar Press+" — above the records, on every screen, whichever
                collection was open. Here it sits on the locked shelf itself,
                beside the six rows it is describing, and costs the records
                nothing. A reader on the full plan never sees it, because the
                shelf has nothing locked on it. */}
            {mode === "app" && upgradeable.length ? (
              <a className="cp-rail__get" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
                Get {upgradeable.length} more <span aria-hidden="true">&#8594;</span>
              </a>
            ) : null}
          </span>
          <ul className="cp-rail__list">
            {entries.map((entry) => {
              const on = entry.id === selectedId;
              // In preview nothing is locked: there is no subscription to
              // measure against, and greying half the catalogue on the door
              // answers a question nobody asked yet.
              const pending = mode === "app" && Boolean(sampleUnavailableReason(entry.id));
              const locked = mode === "app" && !pending && !canOpenDataset(user, entry);
              return (
                <li key={entry.id}>
                  <button
                    type="button"
                    className={`cp-rail__item${on ? " is-on" : ""}${locked ? " is-locked" : ""}${pending ? " is-pending" : ""}`}
                    aria-pressed={on}
                    onClick={() => onSelect(entry)}
                    // Preview only where changing the specimen cannot move
                    // the rail. Touch compatibility hover/focus can otherwise
                    // shift the target before the tap commits its selection.
                    aria-describedby={tip?.entry.id === entry.id ? `cp-railtip-${entry.id}` : undefined}
                    onPointerEnter={(event) => {
                      if (event.pointerType === "mouse" && canHover()) showTip(entry, event.currentTarget);
                      if (onPoint && event.pointerType === "mouse" && window.matchMedia("(min-width: 1101px) and (hover: hover) and (pointer: fine)").matches) onPoint(entry.id);
                    }}
                    onPointerLeave={hideTip}
                    onFocus={(event) => {
                      if (!event.currentTarget.matches(":focus-visible")) return;
                      showTip(entry, event.currentTarget);
                      if (onPoint && window.matchMedia("(min-width: 1101px)").matches) onPoint(entry.id);
                    }}
                    onBlur={hideTip}
                    onKeyDown={(event) => { if (event.key === "Escape") hideTip(); }}
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
                    {/* A publication hold is distinct from a plan boundary:
                        never promise an upgrade for a release that has no
                        self-service preview. */}
                    {pending ? <span className="cp-rail__lock">Pending</span> : null}
                    {locked ? <span className="cp-rail__lock">Plus</span> : null}
                  </button>
                </li>
              );
            })}
          </ul>
          </div>
        );
      })}
    </nav>
  );
}
