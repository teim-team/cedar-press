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
//   reach every one      the chips are the collections each sentence
//                        names, never one added to give a collection a turn
//                        (owner, 2026-09-26). Whether every live collection
//                        is named somewhere is a review report
//                        (`uncoveredIds`, printed by the tests), and the
//                        hero viewer's rail still lists all of them.
//   the plan split       a Cedar Press+ collection's chip carries the plus,
//                        in the same raised treatment as the plan's name
//                        (`TierName`), and the description line names the
//                        plan.
//   say what it holds    the selected collection's one-line description sits
//                        under the band, so chip, frame and description stay
//                        tied together.
//
// THE CARD (owner's brief, 2026-09-26, second pass): an outcome as the
// headline, what Cedar Press lets that audience understand, the collections
// that support it as chips, and a duotone photograph from Lumecon's sector
// image system as a panel beside the text, not a thumbnail. The panel
// alternates sides from one use case to the next on a wide screen and sits
// on top as a banner on a phone. Copy and imagery are `AUDIENCE_JOBS`
// (`pressJobs.js`); the photographs, their sizes and licensing are
// `pressImagery.js` and docs/IMAGE_LICENSES.md.
//
// PHOTOGRAPHS AND THE PAGE'S WEIGHT
// The band sits below the first screen, so every photograph is lazy and
// none can be the page's largest paint. A photograph is only put in the page
// once its use case has been shown or is next in the rotation, so a visitor
// who never scrolls here downloads none of them and one who watches the
// rotation downloads one ahead. The panel's size comes from the grid, never
// from the image, so a photograph arriving late moves nothing. A use case
// with several photographs shows the next on each visit (`imageFor`), never
// while it is on screen.
//
// ROTATION (rules in `pressRotation.js`, held by its tests): a step every
// eight seconds while the band is on screen; paused while it is hovered or
// holds focus; stopped for good by any choice, including a chip; never under
// prefers-reduced-motion. Rotation changes the EXAMPLE only, never the
// selected collection: only a visitor's click does that. Every example is
// laid in the same grid cell and only the chosen one is shown, so the band is
// as tall as its longest example on every step and nothing below it moves.

import { useEffect, useReducer, useRef, useState } from "react";

import { coverageLabel } from "../../features/grove/pressAccess";
import { PRESS_TIERS } from "../../features/grove/pressCatalog";
import { imageSources } from "../../features/grove/pressImagery";
import { BAND_NOTE, visibleAudiences } from "../../features/grove/pressJobs";
import {
  INITIAL_ROTATION,
  ROTATE_MS,
  counterLabel,
  imageFor,
  rotationReducer,
  shouldRotate,
} from "../../features/grove/pressRotation";
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

/**
 * The photograph beside a use case: the 3:2 cut for the side panel and the
 * 5:2 banner on a phone. Decorative, so it carries no alternative text; the
 * door says once that its photography is illustrative.
 */
function UseCaseImage({ slug }) {
  const image = imageSources(slug);
  if (!image) return null;
  return (
    <picture>
      <source media="(max-width: 720px)" srcSet={image.wideSrcSet} sizes="100vw" />
      <img
        src={image.src}
        srcSet={image.srcSet}
        sizes="(max-width: 1100px) 38vw, 520px"
        width={image.width}
        height={image.height}
        alt=""
        loading="lazy"
        decoding="async"
        data-image={slug}
      />
    </picture>
  );
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
  // Whether this band currently holds a preview in the parent. Clearing keys
  // off this, not off `hoverPreview`: the media can flip (a narrowed window, a
  // pointer change) between the hover that set a preview and the leave that
  // should clear it, and a guard on the current media then skipped the clear,
  // leaving the frame on a collection the address does not name (PR #131,
  // Codex thread 4113064956).
  const previewingRef = useRef(false);
  const preview = (id) => {
    previewingRef.current = id != null;
    onPoint?.(id);
  };
  const clearPreview = () => {
    if (previewingRef.current) preview(null);
  };
  useEffect(() => {
    if (!wide || !fine) clearPreview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wide, fine]);
  const rootRef = useRef(null);
  const tabRefs = useRef([]);
  const rotating = shouldRotate(state, { reducedMotion, total });
  // How many times each use case has been the one in view, so a use case with
  // several photographs shows the next one each time it comes round. Updated
  // while rendering, on a change of index, rather than in an effect: it is
  // derived from the index and needs no second pass.
  const [seen, setSeen] = useState(() => ({ index: 0, visits: { 0: 1 } }));
  if (seen.index !== state.index) {
    setSeen({ index: state.index, visits: { ...seen.visits, [state.index]: (seen.visits[state.index] ?? 0) + 1 } });
  }
  const upNext = rotating ? (state.index + 1) % total : -1;
  // The photograph a panel carries, or none. Every use case shown so far
  // keeps the one it showed (so a panel fading out keeps its photograph until
  // it has gone), and the next in the rotation already holds the one it is
  // about to show, so the crossfade never waits on a download.
  const slugFor = (useCase, i) => {
    const visits = seen.visits[i] ?? 0;
    if (i === upNext && i !== state.index) return imageFor(useCase.imagePool, visits + 1);
    return visits ? imageFor(useCase.imagePool, visits) : null;
  };

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
  // The line under the card describes a collection ON the card: the one in
  // hand when the card names it (a chip pointed at or clicked), otherwise
  // the card's first chip. It follows the use case as it changes, and never
  // describes a collection the card does not show, even when the hero frame
  // holds one picked elsewhere.
  const card = AUDIENCES[state.index] ?? null;
  const described = card
    ? card.collections.find((entry) => entry.id === selected?.id) ?? card.collections[0] ?? null
    : selected;
  const tier = described ? TIER_BY_SHELF[described.shelf] : null;

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
        {AUDIENCES.map((useCase, i) => {
          const on = i === state.index;
          const slug = slugFor(useCase, i);
          return (
            <div
              key={useCase.id}
              id={`cp-aud-panel-${useCase.id}`}
              role="tabpanel"
              aria-labelledby={`cp-aud-tab-${useCase.id}`}
              className={`cp-aud__panel${on ? " is-on" : ""}`}
              aria-hidden={on ? undefined : "true"}
              data-audience={useCase.id}
              data-version={useCase.version}
              data-side={i % 2 ? "end" : "start"}
              inert={on ? undefined : true}
            >
              <div className="cp-aud__media" aria-hidden="true">
                {slug ? <UseCaseImage slug={slug} /> : null}
              </div>
              <div className="cp-aud__text">
              {/* Who, and the job it is for, from the shared vocabulary. */}
              <p className="cp-aud__label">
                <span>{useCase.audience}</span>
                {useCase.job ? <span className="cp-aud__job">{useCase.job}</span> : null}
              </p>
              <p className="cp-aud__outcome">{useCase.outcome}</p>
              <p className="cp-aud__use">{useCase.explanation}</p>
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
                onPointerLeave={(event) => { if (event.pointerType === "mouse") clearPreview(); }}
                onBlur={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget)) clearPreview();
                }}
              >
                {useCase.collections.map((entry) => {
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
                        onPointerEnter={(event) => { if (hoverPreview && event.pointerType === "mouse") preview(entry.id); }}
                        onFocus={(event) => { if (wide && event.currentTarget.matches(":focus-visible")) preview(entry.id); }}
                      >
                        <span className="cp-aud__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id] ?? null}</span>
                        <ChipName entry={entry} />
                      </button>
                    </li>
                  );
                })}
              </ul>
              </div>
            </div>
          );
        })}
      </div>

      <div className="cp-aud__tabs" role="tablist" aria-label="Audiences" ref={tabsRef}>
        {AUDIENCES.map((useCase, i) => {
          const on = i === state.index;
          return (
            <button
              key={useCase.id}
              ref={(node) => { tabRefs.current[i] = node; }}
              type="button"
              role="tab"
              id={`cp-aud-tab-${useCase.id}`}
              aria-selected={on}
              aria-controls={`cp-aud-panel-${useCase.id}`}
              tabIndex={on ? 0 : -1}
              className={`cp-aud__tab${on ? " is-on" : ""}`}
              onClick={() => choose(i)}
              onKeyDown={(event) => onTabKey(event, i)}
            >
              {useCase.audience}
            </button>
          );
        })}
      </div>

      {/* The card's collection, in the owner's words. Live once the visitor
          is driving the band, so a reader who cannot see the frame hears what
          was picked, and is not read a new description every eight seconds
          while the rotation turns it. */}
      <p className="cp-aud__note" aria-live={state.stopped ? "polite" : "off"} data-collection={described?.id}>
        {described ? (
          <>
            <b>{described.name}.</b> {described.blurb}{" "}
            <span className="cp-aud__meta">
              {coverageLabel(described)}
              {tier ? <> &middot; <TierName name={tier.name} /></> : null}
            </span>
          </>
        ) : null}
      </p>
      <p className="cp-aud__quiet">{BAND_NOTE}</p>
    </section>
  );
}
