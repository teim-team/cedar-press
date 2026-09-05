// REVIEW OWNER: Havala
//
// The shelves.
//
// One full-bleed band per tier, alternating filled and plain, so the tiers
// are what divide the page.
//
// A band is two halves. On the left the tier says what it is and lays out its
// collections as square badges. On the right, the space beside them is the
// reader: hover or focus a badge and it tells you what that collection is,
// how far back it goes and whether you can take it right now. That space used
// to be empty, and a square cannot say what a collection is without turning
// back into the card this replaced.
//
// A badge opens its collection in the viewer below and lights up; the
// reader beside the grid describes the collection and carries its sample
// download, on every pointer. That replaced "a badge is the download"
// (2026-09-05 review): a reader who clicks a collection wants to see its
// records, and the file is one more click in the panel that says what it
// is. A locked badge clicks too: it walks you to the panel that says what
// opens it. What's New is the one page that tracks changes.
//
// THE TWO SHELVES INVERT
// Cedar Press sits on teal with white tiles and teal marks; Cedar Press+ sits
// on white with teal tiles and white marks. Same two colours both times,
// swapped, which is what makes them read as one set rather than as an
// available thing and a greyed-out thing. A locked tile looks like its
// shelf; the band's own eyebrow and the reader panel carry the lock.
//
// Tiles lay out six across on a wide screen, one row a shelf, so the two
// tiers read as two rows of six; below that width the grid wraps by itself.
//
// THE ACTIVE COLLECTION IS SHARED, AND SELECTION IS NOT HOVER
// The shelf holds two things: the collection the pointer is on (the reader
// follows it) and the collection the viewer below is showing (its tile
// stays lit). Clicking a tile selects it in the viewer; choosing one in the
// viewer lights its tile; hovering changes what is described, never what
// is selected.
//
// FILTERED TO DATA, THIS IS THE READER'S OWN SHELF
// No locked band and no Cedar Grove. Somebody who asked to see the
// collections asked for the ones they can open, and answering with an upsell
// answers a different question. Everything else still shows both.
//
// The lock is a client-side affordance. `pressAccess` says so in its own
// header; the server has to answer identically before real data sits behind
// any of this.

import { useEffect, useLayoutEffect, useRef, useState } from "react";

// Whether this device points with a finger: no hover means the point-to-read
// affordance below becomes tap-to-read, and a tile's download moves one tap
// further so nobody takes a file before reading what it is.
const COARSE = typeof window !== "undefined" && !!window.matchMedia?.("(hover: none)").matches;

import { appUrl } from "../../features/grove/appLink.js";
import { EVENT, track } from "../../features/grove/telemetry.js";
import { canOpenDataset, coverageFrom, coverageLabel } from "../../features/grove/pressAccess";
import { downloadAll, downloadCsv, hasReleaseFile } from "../../features/grove/pressDownload";
import {
  GROVE_CAPABILITIES,
  GROVE_PUBLIC_DATA,
  PRESS_CATALOG_BY_ID,
  PRESS_TIERS,
  collectionsOnShelf,
} from "../../features/grove/pressCatalog";
import { freshnessLine } from "../../features/grove/pressReleases";
import { TBN_PLANS_URL } from "../../features/grove/pressArticles";
import { LAUNCH_COLLECTION } from "../../features/grove/collection";
import { COLLECTION_ICONS } from "./pressCollectionIcons";
import PressExplore from "./PressExplore";
import { TierName } from "./TierName";

/**
 * Cedar Grove is not a fourth shelf holding one collection. It carries
 * everything Cedar Press does, its own exclusives, and the harmonized public
 * data, so its band shows all of that rather than the single badge that made
 * the tier look smaller than the two above it.
 */


/**
 * Marks the band once it has been scrolled to, so the badges can arrive
 * rather than being there already. One-way: a band that has been seen stays
 * seen, because re-animating on the way back up is the thing that makes a
 * page feel restless.
 */
function useReveal() {
  const ref = useRef(null);
  // Anywhere without IntersectionObserver starts revealed, decided at mount
  // rather than corrected by an effect: a band that flashes in on a browser
  // that cannot observe it is worse than one that was simply always there.
  const [seen, setSeen] = useState(() => typeof IntersectionObserver === "undefined");
  // A band that is already on the first screen was never scrolled to, so it
  // is not a reveal — same reasoning as useFadeIn. It is marked seen before
  // the browser paints and its badges do not run their staggered rise, so
  // the shelf is part of the page arriving rather than a second arrival
  // 45ms-per-badge behind it.
  const [instant, setInstant] = useState(false);
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node || seen) return;
    // Flushed before paint, so the band never renders at opacity 0 first.
    if (node.getBoundingClientRect().top < (window.innerHeight || 0) * 1.1) {
      setInstant(true);
      setSeen(true);
    }
  }, [seen]);
  useEffect(() => {
    const node = ref.current;
    if (!node || seen) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setSeen(true);
          observer.disconnect();
        }
      },
      { rootMargin: "-8% 0px -8% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [seen]);
  return [ref, seen, instant];
}

function Badge({ entry, open, onEnter, active, selected, index, onLocked, onOpen }) {
  const className = `cp-badge${active || selected ? " is-on" : ""}${selected ? " is-selected" : ""}${open ? " cp-badge--act" : " cp-badge--locked"}`;
  // The selection is sticky on every pointer, not only touch: the read panel
  // carries its own actions (Ask Cedar, the touch download), and clearing on
  // mouse-leave or blur unmounted those buttons under the very pointer
  // traveling to click them. The panel changes when another tile is pointed
  // at, never back to the idle hint.
  const watch = { onMouseEnter: onEnter, onFocus: onEnter };
  const inner = (
    <>
      <span className="cp-badge__mark" aria-hidden="true">{COLLECTION_ICONS[entry.id]}</span>
      <span className="cp-badge__name"><TierName name={entry.short || entry.name} /></span>
    </>
  );
  // The badges arrive in sequence rather than all at once, which is what
  // makes a grid read as a shelf filling up instead of a page repainting.
  const style = { "--i": index };

  // Every tile answers a click on both shelves, and the cue says what the
  // answer is: an owned tile hands over the file (the down arrow is the
  // download), a locked one walks you to what opens it. Only the symbol
  // differs, so the two shelves keep one hover language.
  if (!open) {
    return (
      <li style={style}>
        <button type="button" className={className} onClick={onLocked} {...watch}>
          {inner}
          <span className="cp-badge__cue" aria-hidden="true">&#8594;</span>
          <span className="cp-badge__sr">See what opens {entry.name}</span>
        </button>
      </li>
    );
  }
  return (
    <li style={style}>
      <button type="button" className={className} onClick={() => onOpen(entry)} aria-pressed={selected} {...watch}>
        {inner}
        <span className="cp-badge__cue" aria-hidden="true">&#8595;</span>
        <span className="cp-badge__sr">Open {entry.name} in the viewer below</span>
      </button>
    </li>
  );
}

/** Whether Cedar has a profile to answer from for this collection. Every
 *  catalog collection has one now: the launch four answer from their releases
 *  and the rest from their catalog entries (collection_profiles.py), so only
 *  an entry outside the catalog — the harmonized public data — goes without
 *  the button. */
function hasCedarProfile(id) {
  return Boolean(PRESS_CATALOG_BY_ID[id]) || LAUNCH_COLLECTION.some((d) => d.id === id);
}

/** What the reader says about the collection under the cursor. */
function Detail({ entry, owned }) {
  return (
    <div className="cp-read__on">
      <span className="cp-read__cap">
        {entry.kind === "public" ? "Harmonized public data" : "Cedar collection"}
      </span>
      <h4 className="cp-read__name"><TierName name={entry.name} /></h4>
      <p className="cp-read__blurb">{entry.blurb}</p>
      {entry.linkage ? (
        <p className="cp-read__link">
          <span className="cp-read__linkcap">The link</span>
          {entry.linkage}
        </p>
      ) : null}
      <p className="cp-read__foot">
        {coverageLabel(entry)}
        {" · "}
        {freshnessLine(entry.id) || (owned ? "Opens in the viewer below" : "Locked")}
      </p>
      {/* The download lives here, on every pointer: the panel says what the
          file is before the finger or the cursor takes it. "Sample", not
          the collection's name alone: what downloads is ten real rows of the
          collection's flagship table, not the collection. */}
      {owned ? (
        <button type="button" className="cp-read__act" onClick={() => downloadCsv(entry)}>
          <span aria-hidden="true">&#8595;</span>{" "}
          {hasReleaseFile(entry)
            ? `Download a ten-row sample of ${entry.short || entry.name}`
            : "Download the collection description (sample pending)"}
        </button>
      ) : null}
      {/* Cedar, already scoped: the reader looking at this description is
          one click from asking how the collection was built or what its
          headline figures are, without restating which collection. The
          event reaches the floating control without a prop path. */}
      {hasCedarProfile(entry.id) ? (
        <button
          type="button"
          className="cp-read__cedar"
          onClick={() =>
            window.dispatchEvent(
              new CustomEvent("cedar:ask-collection", {
                detail: { id: entry.id, name: entry.name },
              }),
            )
          }
        >
          Ask Cedar about this collection <span aria-hidden="true">&#8594;</span>
        </button>
      ) : null}
    </div>
  );
}


function Band({ tier, user, index, hovered, setHovered, selectedId, onPick }) {
  const entries = collectionsOnShelf(tier.shelf);

  // Off the tier's own shelf, never off its first entry: Grove's band leads
  // with the collections Cedar Press also carries, so asking about entry
  // zero told a Cedar Press reader that Cedar Grove was their shelf.
  const owned = canOpenDataset(user, { shelf: tier.shelf });
  // The same years whether or not the reader owns the shelf: a locked band
  // shows what is inside it, and what is inside it does not shrink when it
  // opens. Rosters contribute nothing here — `coverageFrom` returns null for
  // them, and a shelf's earliest year must not be a harvest date.
  const starts = entries.map((entry) => coverageFrom(entry)).filter(Boolean);
  const from = starts.length ? Math.min(...starts) : null;
  // The reader follows the pointer; with nothing under it, it describes
  // the collection the viewer is showing.
  const active = entries.find((entry) => entry.id === (hovered ?? selectedId)) || null;
  const [ref, seen, instant] = useReveal();

  // A locked tile's click walks the reader to the answer: the panel that
  // says what the collection is and carries the way in. The ring is so the
  // eye lands there even when the panel was already on screen.
  const readRef = useRef(null);
  const [pulse, setPulse] = useState(false);
  const pointAtUpgrade = () => {
    track(EVENT.lockedCollectionTapped, { shelf: tier.shelf });
    readRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    setPulse(true);
    window.setTimeout(() => setPulse(false), 900);
  };

  // A tile selects its collection in the viewer below and lights; the
  // reader keeps describing it, with the download, until the pointer moves
  // to another tile.
  const openTile = (entry) => {
    track(EVENT.collectionViewed, { collection: entry.id, shelf: tier.shelf });
    setHovered(entry.id);
    onPick(entry.id);
  };

  return (
    <section
      ref={ref}
      className={`cp-band cp-band--${index % 2 === 0 ? "fill" : "plain"}${seen ? " is-in" : ""}${instant ? " cp-reveal--now" : ""}`}
      aria-label={tier.name}
    >
      <div className="cp-band__in">
        {/* What this band is, top right, in the same line as the eyebrow. A
            reader scanning for the download should not have to infer it from
            a grid of squares. */}
        <div className="cp-band__head">
        <div className="cp-band__id">
          <span className="cp-band__eyebrow">{owned ? "Your shelf" : "Locked"}</span>
          <h3 className="cp-band__name"><TierName name={tier.name} /></h3>
          <p className="cp-band__q">{tier.question}</p>
          {/* No price here: Tribal Business News owns Press payment, renewal
              and upgrades, and a number embedded in this catalog goes stale
              the moment the seller changes theirs. The CTA below walks the
              reader to the canonical price. */}
          {owned || tier.id === "grove" ? null : (
            <p className="cp-band__price">Sold through Tribal Business News</p>
          )}
          {owned || tier.id !== "grove" ? null : (
            <p className="cp-band__price">${tier.price.toLocaleString("en-US")} a year</p>
          )}
          <p className="cp-band__promise">{tier.promise}</p>
          {/* "As far back as" with an asterisk, not "back to": the year is
              the deepest single collection, the shelf's collections reach
              back different distances, and a line that promises the whole
              shelf at that depth promises data the other collections do
              not hold. The footnote sends the reader to the panel, which
              gives each collection its own dates. */}
          <p className="cp-band__facts">
            {entries.length} collections
            {from ? ` · records as far back as ${from}*` : ""}
            {owned ? " · yours to download" : ""}
          </p>
          {from ? (
            <p className="cp-band__vary">
              * Coverage varies by collection; {COARSE ? "tap" : "point at"} a tile for its dates.
            </p>
          ) : null}
        </div>
        <span className="cp-kind cp-kind--data">Collections you download</span>
        </div>

        <ul
          className="cp-band__grid"
          style={{ "--cols": Math.min(entries.length, 6) }}
        >
          {entries.map((entry, position) => (
            <Badge
              key={entry.id}
              index={position}
              entry={entry}
              open={owned}
              active={active?.id === entry.id}
              selected={selectedId === entry.id}
              onEnter={() => setHovered(entry.id)}
              onLocked={pointAtUpgrade}
              onOpen={openTile}
            />
          ))}
        </ul>

        {owned ? (
          <p className="cp-band__all">
            <button type="button" className="cp-band__allbtn" onClick={() => { track(EVENT.shelfDownloadedAll, { shelf: tier.shelf, count: entries.length }); downloadAll(entries); }}>
              <span aria-hidden="true">&#8595;</span> Download all {entries.length} samples
            </button>
          </p>
        ) : null}

        {/* Live, so a screen reader hears what the cursor shows. Polite, so
            it never cuts in while someone is reading something else. */}
        <aside ref={readRef} className={`cp-read${pulse ? " is-pulse" : ""}`} aria-live="polite">
          {active ? (
            <Detail entry={active} owned={owned} />
          ) : (
            <div className="cp-read__idle">
              <span className="cp-read__cap">
                {owned ? "Your collections" : <>Inside <TierName name={tier.name} /></>}
              </span>
              <p className="cp-read__hint">
                {COARSE
                  ? "Tap a collection to see what it holds."
                  : "Point at a collection to see what it holds."}
                {owned ? " Click it to browse its records below; its sample download is here." : ""}
              </p>
            </div>
          )}
          {owned ? null : tier.id === "grove" ? (
            // Grove is Lumecon-sold, so its door is the app's plan page.
            <a className="cp-band__cta" href={appUrl("/app/settings?tab=plan")} target="_blank" rel="noreferrer">
              Get <TierName name={tier.name} /> <span aria-hidden="true">&#8594;</span>
            </a>
          ) : (
            // Press tiers are sold by Tribal Business News; /app cannot
            // perform this upgrade, so the click goes to the plans page
            // where the action actually lives.
            <a className="cp-band__cta" href={TBN_PLANS_URL} target="_blank" rel="noreferrer">
              Get <TierName name={tier.name} /> at Tribal Business News{" "}
              <span aria-hidden="true">&#8594;</span>
            </a>
          )}
        </aside>
      </div>
    </section>
  );
}

/**
 * Cedar Grove, teased rather than shelved.
 *
 * This used to lead with Gaming Intelligence as the Grove exclusive, with a
 * split of what Cedar Press showed and what Grove opened. That promise was
 * withdrawn on 2026-09-04: the collection is still being built, and a
 * storefront that previews it is selling a cadence and a scope nobody has
 * measured. What is left is the true case for Grove, which is not one
 * collection but what it does with all of them: the capabilities, and the
 * harmonized public data it carries beside them.
 */
function GroveTeaser({ tier }) {
  const [ref, seen, instant] = useReveal();
  return (
    // id="grove": the address of the Cedar Grove case. Article figures say
    // "Built in Cedar Grove. Make your own" and land here, on the section
    // that argues for it, rather than on the app route a Press reader
    // cannot open.
    <section ref={ref} id="grove" className={`cp-gt${seen ? " is-in" : ""}${instant ? " cp-reveal--now" : ""}`} aria-label="Cedar Grove">
      <div className="cp-gt__head">
        <div>
          <span className="cp-sec__band">Cedar Grove</span>
          <h3 className="cp-gt__title">Ready to analyze it and share it across your organization?</h3>
          <p className="cp-gt__q">{tier.question}</p>
        </div>
        <div>
          <p className="cp-gt__body">
            Cedar Grove is the environment the collections were built for. Visualize and analyze
            across all of them at once, put the results in front of everyone you work with and
            get every dataset Lumecon builds from here as it lands.
          </p>
          {/* The price with the pitch, where deciding happens; it was a
              footnote at the bottom of the section. */}
          <p className="cp-gt__pricehead">
            ${tier.price.toLocaleString("en-US")} a year · unlimited users in one organization
          </p>
        </div>
      </div>

      <ul className="cp-gt__caps">
        {GROVE_CAPABILITIES.map((item) => <li key={item}>{item}</li>)}
      </ul>

      {/* The public data Grove harmonizes beside the collections, as one
          line each. Listed rather than badged: infrastructure is part of
          the case for Grove, not the headline of it. */}
      <ul className="cp-gt__public" aria-label="Harmonized public data in Cedar Grove">
        {GROVE_PUBLIC_DATA.map((entry) => (
          <li key={entry.id}>
            <span className="cp-gt__publicname">{entry.name}</span>
            <span className="cp-gt__publicblurb">{entry.blurb}</span>
          </li>
        ))}
      </ul>

      <p className="cp-gt__act">
        <a className="cp-band__cta" href={appUrl("/app/grove")} target="_blank" rel="noreferrer">
          Explore Cedar Grove <span aria-hidden="true">&#8594;</span>
        </a>
      </p>
    </section>
  );
}

/**
 * Filtered to Data, this is a reader's own shelf and nothing else: no locked
 * band, no Cedar Grove. Somebody who asked to see the collections asked for
 * the ones they can open, and answering with an upsell is answering a
 * different question.
 */
export default function PressShelf({ user }) {
  const shelves = PRESS_TIERS.filter((tier) => tier.storefront);
  const grove = PRESS_TIERS.find((tier) => !tier.storefront);
  const [hovered, setHovered] = useState(null);
  // What the viewer shows (its tile stays lit), and the latest tile click,
  // numbered so clicking the same tile twice scrolls to the viewer twice.
  const [selectedId, setSelectedId] = useState(null);
  const [pick, setPick] = useState(null);
  const onPick = (id) => setPick((prev) => ({ id, n: (prev?.n ?? 0) + 1 }));
  return (
    <div id="catalog" className="cp-bands">
      {shelves.map((tier, index) => (
        <Band key={tier.id} tier={tier} user={user} index={index} hovered={hovered} setHovered={setHovered} selectedId={selectedId} onPick={onPick} />
      ))}
      <PressExplore user={user} pick={pick} onActive={setHovered} onSelected={setSelectedId} />
      {grove ? <GroveTeaser tier={grove} /> : null}
    </div>
  );
}
