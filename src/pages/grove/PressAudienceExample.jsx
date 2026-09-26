// REVIEW OWNER: Havala
//
// Pick a use case, see what feeds it, click through to the data.
//
// One audience at a time (owner's brief, 2026-09-26, section 3): its task in
// one sentence and the collections that task combines, as chips with their
// marks. It sits in the slot the door's collection shelf used to hold, under
// the hero and before the provenance band. The owner's ruling of the same day
// replaced that shelf, because the hero viewer already lists and shows the
// collections, and the space under it is better spent on how they get used.
//
// WHAT THE SHELF DID, AND WHERE EACH JOB WENT
// The viewer renders a real 1280px window scaled to fit, so its rail rows are
// about seventeen pixels tall: visible, not really pointable. The shelf was
// the full-size way to drive it. That job is the chips now:
//
//   drive the viewer     pointing at a chip previews its collection in the
//                        frame (`onPoint`); a click commits it (`onPick`, the
//                        same `pick()` the shelf called: `?collection=`, the
//                        frame and the `collectionViewed` event). Leaving the
//                        chips puts the committed collection back.
//   reach every one      every live collection is cited by at least one
//                        shown audience, held by `uncoveredIds` in the tests
//                        rather than by hand, and every audience is one tap
//                        away in the selector.
//   the plan split       a Cedar Press+ collection's chip carries the plus,
//                        in the same raised treatment as the plan's name
//                        (`TierName`), and the description line names the
//                        plan.
//   say what it holds    the selected collection's one-line description sits
//                        under the band, so chip, frame and description stay
//                        tied together.
//
// ROTATION (rules in `pressAudiences.js`, held by its tests): a step every
// eight seconds while the band is on screen; paused while it is hovered or
// holds focus; stopped for good by any choice, including a chip; never under
// prefers-reduced-motion. Rotation changes the EXAMPLE only, never the
// selected collection: only a visitor's click does that. Every example is
// laid in the same grid cell and only the chosen one is shown, so the band is
// as tall as its longest example on every step and nothing below it moves.

import { useEffect, useReducer, useRef, useState } from "react";

import { coverageLabel } from "../../features/grove/pressAccess";
import {
  INITIAL_ROTATION,
  ROTATE_MS,
  counterLabel,
  rotationReducer,
  shouldRotate,
  visibleAudiences,
} from "../../features/grove/pressAudiences";
import { PRESS_TIERS } from "../../features/grove/pressCatalog";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import { TierName } from "./TierName";

const AUDIENCES = visibleAudiences();
const REDUCED = "(prefers-reduced-motion: reduce)";
// Where a preview cannot move the page. Above 1100px the hero frame is a
// fixed 16:10 window and the release specimen floats over its corner, so
// swapping the collection in them changes no height. At or below 1100 the
// specimen joins the flow above the frame (its height differs by collection)
// and at 720 the frame itself becomes a long fluid column; a preview there
// would shift the chip out from under the pointer and the tap with it. So
// below this, a chip commits on click and never previews.
const PREVIEW_WIDTH = "(min-width: 1101px)";
const FINE_POINTER = "(hover: hover) and (pointer: fine)";
const TIER_BY_SHELF = Object.fromEntries(PRESS_TIERS.filter((tier) => tier.storefront).map((tier) => [tier.shelf, tier]));

function useMedia(query) {
  const read = () => (typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia(query)
    : null);
  const [matches, setMatches] = useState(() => Boolean(read()?.matches));
  useEffect(() => {
    const mq = read();
    if (!mq) return undefined;
    const onChange = () => setMatches(mq.matches);
    onChange();
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);
  return matches;
}

/** A chip's name, with the plan's raised plus when the collection is Cedar Press+. */
function ChipName({ entry }) {
  const name = entry.short || entry.name;
  if (entry.shelf !== "pro") return name;
  // "Prime Contracting+" through the same component that raises the plus on
  // "Cedar Press+", so the mark is the plan's, not a new badge.
  return <TierName name={`${name}+`} />;
}

export default function PressAudienceExample({ selected, onPick, onPoint }) {
  const total = AUDIENCES.length;
  const [state, dispatch] = useReducer(rotationReducer, INITIAL_ROTATION);
  const reducedMotion = useMedia(REDUCED);
  const wide = useMedia(PREVIEW_WIDTH);
  const fine = useMedia(FINE_POINTER);
  const hoverPreview = wide && fine;
  const rootRef = useRef(null);
  const tabRefs = useRef([]);
  const rotating = shouldRotate(state, { reducedMotion, total });

  // Off screen, nothing advances: a visitor who scrolls down to the band
  // starts on the first example, not on whichever one a timer reached.
  useEffect(() => {
    const node = rootRef.current;
    if (!node) return undefined;
    if (typeof IntersectionObserver !== "function") {
      dispatch({ type: "visible", on: true });
      return undefined;
    }
    const observer = new IntersectionObserver(
      ([entry]) => dispatch({ type: "visible", on: entry.isIntersecting }),
      // A third, not a half: on a small phone the band with its note can be
      // taller than the window, and half of it may never fit at once.
      { threshold: 0.3 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  // One timeout per step, restarted whenever the example or a pause changes.
  useEffect(() => {
    if (!rotating) return undefined;
    const timer = window.setTimeout(() => dispatch({ type: "tick", total }), ROTATE_MS);
    return () => window.clearTimeout(timer);
  }, [rotating, state.index, total]);

  // On a phone the audience names scroll sideways in one row. Keep the one in
  // hand in view there, whether a click or the rotation moved it, by
  // scrolling the ROW only: `scrollIntoView` would also scroll the page.
  const tabsRef = useRef(null);
  useEffect(() => {
    const row = tabsRef.current;
    const tab = tabRefs.current[state.index];
    if (!row || !tab || row.scrollWidth <= row.clientWidth) return;
    const left = tab.offsetLeft - row.offsetLeft;
    const right = left + tab.offsetWidth;
    const pad = 16;
    if (left < row.scrollLeft + pad || right > row.scrollLeft + row.clientWidth - pad) {
      row.scrollTo({ left: Math.max(0, left - pad), behavior: reducedMotion ? "auto" : "smooth" });
    }
  }, [state.index, reducedMotion]);

  if (!total) return null;

  const choose = (index, { focus = false } = {}) => {
    dispatch({ type: "select", index, total });
    if (focus) tabRefs.current[index]?.focus();
  };
  // Arrow keys move along the tabs, the pattern a tablist promises.
  const onTabKey = (event, index) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (event.key === "Home") { event.preventDefault(); choose(0, { focus: true }); return; }
    if (event.key === "End") { event.preventDefault(); choose(total - 1, { focus: true }); return; }
    if (!step) return;
    event.preventDefault();
    choose((index + step + total) % total, { focus: true });
  };
  const commit = (entry) => {
    dispatch({ type: "stop" });
    onPick?.(entry);
  };
  const tier = selected ? TIER_BY_SHELF[selected.shelf] : null;

  return (
    <section
      className="cp-aud cp-fade"
      aria-label="Use cases"
      ref={rootRef}
      data-rotating={rotating ? "true" : "false"}
      data-stopped={state.stopped ? "true" : "false"}
      onMouseEnter={() => dispatch({ type: "hover", on: true })}
      onMouseLeave={() => dispatch({ type: "hover", on: false })}
      onFocus={() => dispatch({ type: "focus", on: true })}
      onBlur={(event) => {
        if (!rootRef.current?.contains(event.relatedTarget)) dispatch({ type: "focus", on: false });
      }}
    >
      <div className="cp-aud__head">
        <span className="cp-kicker">Use cases</span>
        <span className="cp-aud__nav">
          <button
            type="button"
            className="cp-aud__step"
            aria-label="Previous use case"
            onClick={() => dispatch({ type: "prev", total })}
          >
            <span aria-hidden="true">&#8592;</span>
          </button>
          <span className="cp-aud__count" aria-hidden="true">{counterLabel(state.index, total)}</span>
          <button
            type="button"
            className="cp-aud__step"
            aria-label="Next use case"
            onClick={() => dispatch({ type: "next", total })}
          >
            <span aria-hidden="true">&#8594;</span>
          </button>
        </span>
      </div>

      {/* Every example occupies the same cell; the chosen one is shown. The
          region only announces once the visitor is driving it, so a screen
          reader is not read a new example every eight seconds. */}
      <div className="cp-aud__stack" aria-live={state.stopped ? "polite" : "off"}>
        {AUDIENCES.map((audience, i) => {
          const on = i === state.index;
          return (
            <div
              key={audience.id}
              id={`cp-aud-panel-${audience.id}`}
              role="tabpanel"
              aria-labelledby={`cp-aud-tab-${audience.id}`}
              className={`cp-aud__panel${on ? " is-on" : ""}`}
              aria-hidden={on ? undefined : "true"}
              data-audience={audience.id}
              data-version={audience.version}
              inert={on ? undefined : true}
            >
              <p className="cp-aud__label">{audience.label}</p>
              <p className="cp-aud__use">{audience.use}</p>
              {/* Pointing previews; only a click commits. Leaving the set
                  hands the frame back to the committed collection.

                  "Pointing" is a mouse hover or keyboard focus, never a
                  finger, and only where a preview cannot move the page
                  (PREVIEW_WIDTH). Measured on a phone: the frame above is a
                  ~2,300px fluid column, previewing on a tap's focus swapped it
                  between the finger going down and coming up, and the tap
                  landed on the section below. A tap commits directly. */}
              <ul
                className="cp-aud__cols"
                aria-label="Collections this uses"
                onPointerLeave={(event) => { if (hoverPreview && event.pointerType === "mouse") onPoint?.(null); }}
                onBlur={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget)) onPoint?.(null);
                }}
              >
                {audience.collections.map((entry) => {
                  const chosen = selected?.id === entry.id;
                  return (
                    <li key={entry.id}>
                      <button
                        type="button"
                        className={`cp-aud__col${chosen ? " is-on" : ""}`}
                        data-collection={entry.id}
                        data-shelf={entry.shelf}
                        aria-pressed={chosen}
                        onClick={() => commit(entry)}
                        onPointerEnter={(event) => { if (hoverPreview && event.pointerType === "mouse") onPoint?.(entry.id); }}
                        onFocus={(event) => { if (wide && event.currentTarget.matches(":focus-visible")) onPoint?.(entry.id); }}
                      >
                        <span className="cp-aud__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
                        <ChipName entry={entry} />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>

      <div className="cp-aud__tabs" role="tablist" aria-label="Audiences" ref={tabsRef}>
        {AUDIENCES.map((audience, i) => {
          const on = i === state.index;
          return (
            <button
              key={audience.id}
              ref={(node) => { tabRefs.current[i] = node; }}
              type="button"
              role="tab"
              id={`cp-aud-tab-${audience.id}`}
              aria-selected={on}
              aria-controls={`cp-aud-panel-${audience.id}`}
              tabIndex={on ? 0 : -1}
              className={`cp-aud__tab${on ? " is-on" : ""}`}
              onClick={() => choose(i)}
              onKeyDown={(event) => onTabKey(event, i)}
            >
              {audience.label}
            </button>
          );
        })}
      </div>

      {/* The collection in hand, in the owner's words. aria-live, so a reader
          who cannot see the frame above still hears what was picked. */}
      <p className="cp-aud__note" aria-live="polite">
        {selected ? (
          <>
            <b>{selected.name}.</b> {selected.blurb}{" "}
            <span className="cp-aud__meta">
              {coverageLabel(selected)}
              {tier ? <> &middot; <TierName name={tier.name} /></> : null}
            </span>
          </>
        ) : null}
      </p>
    </section>
  );
}
